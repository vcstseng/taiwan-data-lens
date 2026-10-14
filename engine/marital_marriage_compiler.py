class MaritalMarriageCompiler:
    MARITAL={"marital_population","marital_status_share","unmarried_share","partnered_share","divorced_stock_share"}
    MARRIAGE={"marriage_person_count","marriage_person_share","same_sex_marriage_person_share"}
    OPS={"snapshot","rank","profile","compare"}

    def compile(self,p):
        m=p["metric"]; op=p["operation"]
        if op not in self.OPS: raise ValueError("unsupported operation")
        if m in self.MARITAL: return self._marital(p)
        if m in self.MARRIAGE: return self._marriage(p)
        raise ValueError("unsupported metric")

    def _scope(self,p):
        s=p.get("scope") or {}; year=p.get("period")
        if year is None: raise ValueError("annual metric requires period/year")
        geo=s.get("geography"); geos=s.get("geographies")
        if p["operation"]=="compare":
            if not isinstance(geos,list) or len(geos)<2: raise ValueError("compare requires geographies")
        elif not geo and not s.get("parent_geography") and s.get("geography_level") not in {"country","county"}:
            raise ValueError("geography or parent_geography required")
        return s,str(year)

    def _filters(self,p,allowed):
        f=p.get("filters") or {}
        bad=set(f)-set(allowed)
        if bad: raise ValueError(f"unsupported filters: {sorted(bad)}")
        return f

    def _marital(self,p):
        s,y=self._scope(p); f=self._filters(p,{"sex","age_band","education","marital_status"})
        params=["{marital_path}",y]; where=["year = ?"]
        if p["operation"]=="compare":
            gs=s["geographies"]; where.append("site_id IN ("+",".join("?"*len(gs))+")"); params+=gs
        elif s.get("geography_level") in {"country","county"}:
            pass  # explicit rollup: aggregate the full fact at the requested level
        elif s.get("geography"): where.append("site_id = ?"); params.append(s["geography"])
        else: where.append("site_id LIKE ?"); params.append(s["parent_geography"]+"%")
        for k,col in [("sex","sex"),("age_band","age_band"),("education","education")]:
            if f.get(k): where.append(f"{col} = ?"); params.append(f[k])
        base=" AND ".join(where); metric=p["metric"]
        if metric=="marital_population":
            if f.get("marital_status"): base+=" AND marital_status = ?"; params.append(f["marital_status"])
            expr="SUM(population)::BIGINT"
        else:
            status={
              "unmarried_share":["未婚"],
              "partnered_share":["有偶_不同性別","有偶_相同性別"],
              "divorced_stock_share":["離婚_不同性別","離婚_相同性別"],
            }.get(metric)
            if metric=="marital_status_share":
                if not f.get("marital_status"): raise ValueError("marital_status_share requires marital_status")
                status=[f["marital_status"]]
            qs=",".join("?"*len(status))
            # CASE placeholders occur before read_parquet(?) in SQL text.
            params=status+params
            expr=f"100.0*SUM(CASE WHEN marital_status IN ({qs}) THEN population ELSE 0 END)/NULLIF(SUM(population),0)"
        geo_expr=self._geography_expr(s.get("geography_level"))
        group="geography"
        sql=f"SELECT year,{geo_expr} AS geography,{expr} AS metric_value FROM read_parquet(?) WHERE {base} GROUP BY year,{group}"
        if p["operation"] in {"rank","profile","compare"}: sql+=" ORDER BY metric_value DESC,geography ASC"
        if p.get("limit") is not None: sql+=" LIMIT ?"; params.append(p["limit"])
        return {"sql":sql,"params":params,"unit":"persons" if metric=="marital_population" else "percent"}

    def _marriage(self,p):
        s,y=self._scope(p); f=self._filters(p,{"sex","age_band","education","nationality","marriage_type"})
        params=["{marriage_path}",y]; where=["year = ?"]
        if p["operation"]=="compare":
            gs=s["geographies"]; where.append("site_id IN ("+",".join("?"*len(gs))+")"); params+=gs
        elif s.get("geography_level") in {"country","county"}:
            pass  # explicit rollup: aggregate the full fact at the requested level
        elif s.get("geography"): where.append("site_id = ?"); params.append(s["geography"])
        else: where.append("site_id LIKE ?"); params.append(s["parent_geography"]+"%")
        for k,col in [("sex","sex"),("age_band","age_band"),("education","education"),("nationality","nationality")]:
            if f.get(k): where.append(f"{col} = ?"); params.append(f[k])
        base=" AND ".join(where); metric=p["metric"]
        if metric=="marriage_person_count":
            if f.get("marriage_type"): base+=" AND marriage_type = ?"; params.append(f["marriage_type"])
            expr="SUM(marriage_count)::BIGINT"
        else:
            if metric=="same_sex_marriage_person_share": typ="相同性別"
            else:
                typ=f.get("marriage_type")
                if not typ: raise ValueError("marriage_person_share requires marriage_type")
            # CASE placeholder occurs before read_parquet(?) in SQL text.
            params=[typ]+params
            expr="100.0*SUM(CASE WHEN marriage_type = ? THEN marriage_count ELSE 0 END)/NULLIF(SUM(marriage_count),0)"
        geo_expr=self._geography_expr(s.get("geography_level"))
        sql=f"SELECT year,{geo_expr} AS geography,{expr} AS metric_value FROM read_parquet(?) WHERE {base} GROUP BY year,geography"
        if p["operation"] in {"rank","profile","compare"}: sql+=" ORDER BY metric_value DESC,geography ASC"
        if p.get("limit") is not None: sql+=" LIMIT ?"; params.append(p["limit"])
        return {"sql":sql,"params":params,"unit":"persons" if metric=="marriage_person_count" else "percent"}


    def _geography_expr(self, level):
        if not level or level == "district":
            return "site_id"
        if level == "county":
            return "regexp_extract(site_id, '^(.+?[縣市])', 1)"
        if level == "country":
            return "'臺灣'"
        raise ValueError(f"unsupported marital/marriage geography_level: {level}")
