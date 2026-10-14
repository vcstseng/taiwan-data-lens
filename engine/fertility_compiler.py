class FertilityCompiler:
    METRICS={"total_fertility_rate","general_fertility_rate","age_specific_fertility_rate"}
    OPS={"snapshot","rank","trend","change","compare","profile"}
    ASFR={
      "15-19":"asfr_15_19","20-24":"asfr_20_24","25-29":"asfr_25_29",
      "30-34":"asfr_30_34","35-39":"asfr_35_39","40-44":"asfr_40_44","45-49":"asfr_45_49",
    }

    def compile(self,p):
        m=p["metric"]; op=p["operation"]
        if m not in self.METRICS or op not in self.OPS: raise ValueError("unsupported fertility metric/operation")
        s=p.get("scope") or {}
        if op=="compare":
            gs=s.get("geographies")
            if not isinstance(gs,list) or len(gs)<2: raise ValueError("compare requires geographies")
        elif op not in {"rank"} and not s.get("geography") and not s.get("parent_geography"):
            raise ValueError("geography or parent_geography required")
        if p.get("filters"): raise ValueError("fertility has no filter dimensions")
        if m=="age_specific_fertility_rate" and op!="profile":
            band=(p.get("parameters") or {}).get("age_band")
            if band not in self.ASFR: raise ValueError("age_specific_fertility_rate requires age_band")
        if op=="profile" and m!="age_specific_fertility_rate": raise ValueError("profile only supported for ASFR")
        if op=="profile": return self._profile(p)
        return self._scalar(p)

    def _field(self,p):
        m=p["metric"]
        if m=="total_fertility_rate": return "total_fertility_rate", "births_per_woman", 0.001
        if m=="general_fertility_rate": return "general_fertility_rate", "per_thousand", 1.0
        band=p["parameters"]["age_band"]
        return self.ASFR[band], "per_thousand", 1.0

    def _where(self,p, time_mode):
        s=p.get("scope") or {}; params=[]; where=[]
        if time_mode=="period": where.append("year = ?"); params.append(str(p["period"]))
        else: where.append("year BETWEEN ? AND ?"); params += [str(p["start_period"]),str(p["end_period"])]
        if p["operation"]=="compare":
            gs=s["geographies"]; where.append("site_id IN ("+",".join("?"*len(gs))+")"); params += gs
        elif s.get("geography"):
            where.append("site_id = ?"); params.append(s["geography"])
        elif s.get("parent_geography"):
            where.append("site_id LIKE ?"); params.append(s["parent_geography"]+"%")
        return " AND ".join(where), params

    def _scalar(self,p):
        field,unit,scale=self._field(p); op=p["operation"]
        mode="period" if op in {"snapshot","rank","compare"} else "range"
        where,params=self._where(p,mode); params=["{fertility_path}"]+params
        expr=f"CAST({field} AS DOUBLE)" + (" / 1000.0" if scale==0.001 else "")
        if op=="change":
            # Rates are compared over time, never summed/averaged across geography.
            params=["{fertility_path}",str(p["start_period"]),str(p["end_period"])]
            s=p.get("scope") or {}; extra=""
            if s.get("geography"): extra=" AND site_id = ?"; params.append(s["geography"])
            elif s.get("parent_geography"): extra=" AND site_id LIKE ?"; params.append(s["parent_geography"]+"%")
            else: raise ValueError("change requires geography or parent_geography")
            conv=" / 1000.0" if scale==0.001 else ""
            sql=(f"SELECT site_id AS geography, "
                 f"MAX(CASE WHEN year = ? THEN CAST({field} AS DOUBLE) END){conv} AS start_value, "
                 f"MAX(CASE WHEN year = ? THEN CAST({field} AS DOUBLE) END){conv} AS end_value, "
                 f"(MAX(CASE WHEN year = ? THEN CAST({field} AS DOUBLE) END)-MAX(CASE WHEN year = ? THEN CAST({field} AS DOUBLE) END)){conv} AS metric_value "
                 f"FROM read_parquet(?) WHERE year IN (?,?)"+extra+" GROUP BY site_id")
            # SQL placeholder order: 4 years, path, 2 years, geography
            tail=params[3:]
            params=[str(p["start_period"]),str(p["end_period"]),str(p["end_period"]),str(p["start_period"]),"{fertility_path}",str(p["start_period"]),str(p["end_period"])] + tail
        else:
            sql=f"SELECT year,site_id AS geography,{expr} AS metric_value FROM read_parquet(?) WHERE {where}"
        if op in {"rank","compare"}: sql += " ORDER BY metric_value " + ("ASC" if p.get("order")=="ascending" else "DESC") + ", geography ASC"
        elif op=="trend": sql += " ORDER BY year ASC, geography ASC"
        elif op=="change": sql += " ORDER BY metric_value " + ("ASC" if p.get("order")=="ascending" else "DESC") + ", geography ASC"
        if p.get("limit") is not None: sql+=" LIMIT ?"; params.append(p["limit"])
        return {"sql":sql,"params":params,"unit":unit}

    def _profile(self,p):
        if p.get("profile_dimension")!="age_band": raise ValueError("ASFR profile requires age_band")
        where,params=self._where(p,"period"); params=["{fertility_path}"]+params
        parts=[]
        for band,col in self.ASFR.items():
            parts.append(f"SELECT year,site_id AS geography,'{band}' AS age_band,CAST({col} AS DOUBLE) AS metric_value FROM base")
        sql=f"WITH base AS (SELECT * FROM read_parquet(?) WHERE {where}) " + " UNION ALL ".join(parts) + " ORDER BY age_band, geography"
        return {"sql":sql,"params":params,"unit":"per_thousand"}
