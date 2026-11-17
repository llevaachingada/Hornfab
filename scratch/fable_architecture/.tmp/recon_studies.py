import pathlib, json, yaml
root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\runs')
for S in sorted(root.glob('study-*')):
    sd = S/'screen'; vd = S/'verify'
    if not sd.is_dir():
        continue
    cfg = yaml.safe_load(open(sd/'config.yaml', encoding='utf8'))
    n_screen = len(list((sd/'designs').glob('*'))) if (sd/'designs').is_dir() else 0
    n_verify = len(list((vd/'designs').glob('*'))) if (vd/'designs').is_dir() else 0
    t = cfg.get('target') or {}
    env = (cfg.get('brief') or {}).get('envelope') or {}
    obj = cfg.get('objective')
    ov = obj.get('version') if isinstance(obj, dict) else cfg.get('objective_version')
    print(S.name, 'screen', n_screen, 'verify', n_verify, '| name', str(cfg.get('name'))[:44],
          '| cov', t.get('coverage_h_deg'), t.get('coverage_v_deg'), '| band', t.get('band_lo_hz'), t.get('band_hi_hz'),
          '| f0', t.get('f0_hz'), t.get('f0_v_hz'), '| env', env, '| objver', ov)
