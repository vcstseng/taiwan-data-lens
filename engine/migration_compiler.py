
class MigrationQueryCompiler:
    METRICS = {"migration_flow_count", "migration_destination_share"}
    OPERATIONS = {"snapshot", "rank", "profile", "trend", "change", "compare"}

    COUNTY_GEOGRAPHIES = {
        "臺北市", "新北市", "桃園市", "臺中市",
        "臺南市", "高雄市", "基隆市", "新竹市",
        "嘉義市", "新竹縣", "苗栗縣", "彰化縣",
        "南投縣", "雲林縣", "嘉義縣", "屏東縣",
        "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣",
        "金門縣", "連江縣",
    }

    def compile(self, plan):
        metric = plan["metric"]
        op = plan["operation"]

        if metric not in self.METRICS:
            raise ValueError("not a migration metric")
        if op not in self.OPERATIONS:
            raise ValueError("unsupported migration operation")

        if op in {"snapshot", "rank", "profile"}:
            return self._compile_point(plan)
        if op == "trend":
            return self._compile_trend(plan)
        if op == "change":
            return self._compile_change(plan)
        return self._compile_compare(plan)

    @staticmethod
    def _filters(plan):
        f = plan.get("filters") or {}
        unknown = set(f) - {"sex", "destination_county"}
        if unknown:
            raise ValueError(f"unsupported migration filters: {sorted(unknown)}")
        return f

    @staticmethod
    def _origin(scope):
        scope = scope or {}
        return scope.get("origin_geography") or scope.get("geography")

    def _where_context(self, period_sql, origin_sql, plan, include_destination=True):
        f = self._filters(plan)
        where = [period_sql, origin_sql]
        vals = []

        if f.get("sex"):
            where.append("sex = ?")
            vals.append(f["sex"])

        if include_destination and f.get("destination_county"):
            where.append("destination_county = ?")
            vals.append(f["destination_county"])

        return where, vals

    def _compile_point(self, plan):
        scope = plan.get("scope") or {}
        origin = self._origin(scope)

        if not origin:
            raise ValueError("migration query requires origin district")

        geography_level = scope.get("geography_level", "district")

        if geography_level not in {"district", "county"}:
            raise ValueError(
                f"unsupported migration geography_level: {geography_level}"
            )

        if (
            geography_level == "county"
            and origin not in self.COUNTY_GEOGRAPHIES
        ):
            raise ValueError(
                "county-level migration requires a valid county/city name"
            )

        period = plan.get("period")
        if not period:
            raise ValueError("point query requires period")

        f = self._filters(plan)

        # Share calculations retain their original district-level semantics.
        if plan["metric"] == "migration_destination_share":
            where = ["period = ?", "origin_district = ?"]
            params = ["{migration_path}", period, origin]

            if f.get("sex"):
                where.append("sex = ?")
                params.append(f["sex"])

            dest_pred = ""
            if f.get("destination_county"):
                dest_pred = "WHERE destination_county = ?"
                params.append(f["destination_county"])

            sql = f"""WITH d AS (
 SELECT period, origin_district AS geography, destination_county,
        SUM(migrant_count)::BIGINT AS destination_count
 FROM read_parquet(?) WHERE {' AND '.join(where)}
 GROUP BY period, origin_district, destination_county
), t AS (
 SELECT period, geography, SUM(destination_count)::BIGINT AS total_count
 FROM d GROUP BY period, geography
)
SELECT d.period,d.geography,d.destination_county,
       100.0*d.destination_count/NULLIF(t.total_count,0) AS metric_value
FROM d JOIN t USING(period,geography)
{dest_pred}
ORDER BY metric_value DESC,d.destination_county ASC"""

        else:
            # County-level aggregation is supported for migration flow profiles.
            # All matching origin districts are summed by destination county.
            if (
                plan["operation"] == "profile"
                and plan["metric"] == "migration_flow_count"
                and geography_level == "county"
            ):
                where = ["period = ?", "origin_district LIKE ?"]
                params = ["{migration_path}", period, origin + "%"]

                if f.get("sex"):
                    where.append("sex = ?")
                    params.append(f["sex"])

                if f.get("destination_county"):
                    where.append("destination_county = ?")
                    params.append(f["destination_county"])

                # origin is restricted to the explicit county/city allowlist above.
                sql = f"""SELECT period,'{origin}' AS geography,destination_county,
SUM(migrant_count)::BIGINT AS metric_value
FROM read_parquet(?) WHERE {' AND '.join(where)}
GROUP BY period,destination_county
ORDER BY metric_value DESC,destination_county ASC"""

            else:
                where = ["period = ?", "origin_district = ?"]
                params = ["{migration_path}", period, origin]

                if f.get("sex"):
                    where.append("sex = ?")
                    params.append(f["sex"])

                if f.get("destination_county"):
                    where.append("destination_county = ?")
                    params.append(f["destination_county"])

                if plan["operation"] == "snapshot":
                    sql = f"""SELECT period,origin_district AS geography,SUM(migrant_count)::BIGINT AS metric_value
FROM read_parquet(?) WHERE {' AND '.join(where)}
GROUP BY period,origin_district"""
                else:
                    sql = f"""SELECT period,origin_district AS geography,destination_county,
SUM(migrant_count)::BIGINT AS metric_value
FROM read_parquet(?) WHERE {' AND '.join(where)}
GROUP BY period,origin_district,destination_county
ORDER BY metric_value DESC,destination_county ASC"""

        if plan.get("limit") is not None:
            sql += "\nLIMIT ?"
            params.append(plan["limit"])

        return {
            "sql": sql.strip(),
            "params": params,
            "source": "{migration_path}",
        }

    def _series_cte(self, plan, origin_mode="single"):
        scope = plan.get("scope") or {}
        f = self._filters(plan)
        start = plan.get("start_period")
        end = plan.get("end_period")

        if not start or not end:
            raise ValueError(
                "temporal query requires start_period and end_period"
            )

        params = ["{migration_path}", start, end]
        where = ["period BETWEEN ? AND ?"]

        if origin_mode == "single":
            origin = self._origin(scope)
            if not origin:
                raise ValueError("temporal query requires origin district")
            where.append("origin_district = ?")
            params.append(origin)

        elif origin_mode == "parent":
            parent = scope.get("parent_geography")
            if not parent:
                raise ValueError(
                    "change across origins requires parent_geography"
                )
            where.append("origin_district LIKE ?")
            params.append(parent + "%")

        if f.get("sex"):
            where.append("sex = ?")
            params.append(f["sex"])

        destination = f.get("destination_county")

        cte = f"""d AS (
 SELECT period,origin_district AS geography,destination_county,
        SUM(migrant_count)::BIGINT AS destination_count
 FROM read_parquet(?) WHERE {' AND '.join(where)}
 GROUP BY period,origin_district,destination_county
), t AS (
 SELECT period,geography,SUM(destination_count)::BIGINT AS total_count
 FROM d GROUP BY period,geography
)"""

        return cte, params, destination

    def _compile_trend(self, plan):
        cte, params, dest = self._series_cte(plan, "single")

        if plan["metric"] == "migration_destination_share":
            if not dest:
                raise ValueError(
                    "destination share trend requires destination_county"
                )

            sql = f"""WITH {cte}
SELECT d.period,d.geography,d.destination_county,
100.0*d.destination_count/NULLIF(t.total_count,0) AS metric_value
FROM d JOIN t USING(period,geography)
WHERE d.destination_county = ?
ORDER BY d.period"""
            params.append(dest)

        else:
            if dest:
                # Sparse facts: absent destination cells are reconstructed as zero.
                sql = f"""WITH periods AS (
 SELECT DISTINCT period FROM read_parquet(?)
 WHERE period BETWEEN ? AND ?
), {cte}, x AS (
 SELECT period,geography,destination_county,destination_count
 FROM d WHERE destination_county = ?
)
SELECT p.period, ? AS geography, ? AS destination_county,
       COALESCE(x.destination_count,0)::BIGINT AS metric_value
FROM periods p LEFT JOIN x USING(period)
ORDER BY p.period"""

                origin = self._origin(plan.get("scope") or {})
                params = [
                    "{migration_path}",
                    plan["start_period"],
                    plan["end_period"],
                    *params,
                    dest,
                    origin,
                    dest,
                ]

            else:
                sql = f"""WITH {cte}
SELECT period,geography,SUM(destination_count)::BIGINT AS metric_value
FROM d GROUP BY period,geography ORDER BY period"""

        return {
            "sql": sql.strip(),
            "params": params,
            "source": "{migration_path}",
        }

    def _compile_change(self, plan):
        if plan["metric"] != "migration_flow_count":
            raise ValueError(
                "migration destination share change not enabled in v0.1"
            )

        cte, params, dest = self._series_cte(plan, "parent")
        start = plan["start_period"]
        end = plan["end_period"]

        dest_where = ""
        if dest:
            dest_where = "WHERE destination_county = ?"
            params.append(dest)

        parent = (plan.get("scope") or {}).get("parent_geography")

        sql = f"""WITH origins AS (
 SELECT DISTINCT origin_district AS geography FROM read_parquet(?)
 WHERE origin_district LIKE ?
), endpoints(period) AS (VALUES (?),(?)),
{cte}, s AS (
 SELECT period,geography,SUM(destination_count)::BIGINT AS metric_value
 FROM d {dest_where} GROUP BY period,geography
), complete AS (
 SELECT e.period,o.geography,COALESCE(s.metric_value,0)::BIGINT AS metric_value
 FROM origins o CROSS JOIN endpoints e
 LEFT JOIN s USING(period,geography)
), p AS (
 SELECT geography,
 MAX(CASE WHEN period = ? THEN metric_value END) AS start_value,
 MAX(CASE WHEN period = ? THEN metric_value END) AS end_value
 FROM complete GROUP BY geography
)
SELECT geography,start_value,end_value,
(end_value-start_value)::BIGINT AS metric_value
FROM p
ORDER BY metric_value DESC,geography ASC"""

        params = ["{migration_path}", parent + "%", start, end, *params]
        params += [start, end]

        if plan.get("limit") is not None:
            sql += "\nLIMIT ?"
            params.append(plan["limit"])

        return {
            "sql": sql.strip(),
            "params": params,
            "source": "{migration_path}",
        }

    def _compile_compare(self, plan):
        scope = plan.get("scope") or {}
        geos = scope.get("geographies")

        if not isinstance(geos, list) or len(geos) < 2:
            raise ValueError("compare requires scope.geographies")

        period = plan.get("period")
        if not period:
            raise ValueError("compare requires period")

        f = self._filters(plan)
        placeholders = ",".join("?" for _ in geos)
        params = ["{migration_path}", period, *geos]
        where = [f"period = ?", "origin_district IN (" + placeholders + ")"]

        if f.get("sex"):
            where.append("sex = ?")
            params.append(f["sex"])

        if plan["metric"] == "migration_destination_share":
            dest = f.get("destination_county")
            if not dest:
                raise ValueError(
                    "destination share compare requires destination_county"
                )

            sql = f"""WITH d AS (
 SELECT period,origin_district AS geography,destination_county,
 SUM(migrant_count)::BIGINT AS destination_count
 FROM read_parquet(?) WHERE {' AND '.join(where)}
 GROUP BY period,origin_district,destination_county
), t AS (
 SELECT period,geography,SUM(destination_count)::BIGINT AS total_count
 FROM d GROUP BY period,geography
)
SELECT d.period,d.geography,d.destination_county,
100.0*d.destination_count/NULLIF(t.total_count,0) AS metric_value
FROM d JOIN t USING(period,geography)
WHERE d.destination_county = ?
ORDER BY metric_value DESC,geography ASC"""
            params.append(dest)

        else:
            if f.get("destination_county"):
                where.append("destination_county = ?")
                params.append(f["destination_county"])

            sql = f"""SELECT period,origin_district AS geography,
SUM(migrant_count)::BIGINT AS metric_value
FROM read_parquet(?) WHERE {' AND '.join(where)}
GROUP BY period,origin_district
ORDER BY metric_value DESC,geography ASC"""

        return {
            "sql": sql.strip(),
            "params": params,
            "source": "{migration_path}",
        }
