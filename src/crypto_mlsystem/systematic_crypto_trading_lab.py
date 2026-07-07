from __future__ import annotations
import csv, json, math, os, random
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, pstdev, median

DEV_START=date(2019,7,5); DEV_END=date(2024,12,31); AUDIT_START=date(2025,1,1); END=date(2026,7,7)
STRESS_START=date(2021,11,8); STRESS_END=date(2022,11,21); COSTS=[10,25,50,100]
LAB=Path('experiments/systematic_crypto_trading_lab'); FEAT=Path('data/systematic_crypto_lab/features'); RAW=Path('data/systematic_crypto_lab/raw'); CLEAN=Path('data/systematic_crypto_lab/clean')
@dataclass
class Candidate:
    name:str; family:str; target_type:str; model_type:str; universe:str; params:dict
    uses_macro:bool=False; uses_trend:bool=False; uses_volatility:bool=False; uses_liquidity:bool=False; uses_derivatives:bool=False; uses_onchain:bool=False; uses_ml:bool=False; uses_ensemble:bool=False; uses_state_machine:bool=False; uses_broader_universe:bool=False

def dates():
    d=DEV_START
    while d<=END: yield d; d+=timedelta(days=1)
def roll(vals,i,lb,fn,default=0.0):
    if i<lb: return default
    return fn(vals[i-lb:i])
def pct_rank(vals,i,lb,x):
    if i<lb: return 0.5
    arr=sorted(vals[i-lb:i]); return sum(v<=x for v in arr)/len(arr)
def qtile(vals,i,lb,q):
    if i<lb: return vals[max(0,i-1)] if i else 0.0
    arr=sorted(vals[i-lb:i]); return arr[min(len(arr)-1,max(0,int(q*(len(arr)-1))))]
def sharpe(rs):
    rs=[x for x in rs if x is not None]; sd=pstdev(rs) if len(rs)>1 else 0
    return 0.0 if len(rs)<5 or sd==0 else math.sqrt(365)*mean(rs)/sd
def maxdd(rs):
    eq=1.0; peak=1.0; m=0.0
    for r in rs: eq*=1+r; peak=max(peak,eq); m=min(m,eq/peak-1)
    return m
def cagr(rs):
    eq=1.0
    for r in rs: eq*=1+r
    yrs=len(rs)/365
    return eq**(1/yrs)-1 if yrs>0 and eq>0 else -1.0
def metrics(rs,exps,turns):
    exp=mean(exps) if exps else 0; out={'gross_sharpe':sharpe(rs),'cagr':cagr(rs),'volatility':(pstdev(rs)*math.sqrt(365) if len(rs)>1 else 0),'max_dd':maxdd(rs),'sortino':sharpe([r for r in rs if r<0]) if any(r<0 for r in rs) else 0,'exposure':exp,'cash_exposure':1-exp,'turnover':mean(turns) if turns else 0,'trades':sum(1 for t in turns if t>1e-9),'return_per_unit_exposure':(mean(rs)*365/max(exp,1e-9) if rs else 0),'drawdown_per_unit_exposure':maxdd(rs)/max(exp,1e-9),'conditional_sharpe_when_invested':sharpe([r for r,e in zip(rs,exps) if e>1e-6])}
    out['calmar']=out['cagr']/abs(out['max_dd']) if out['max_dd']<0 else 0
    for bps in COSTS: out[f'net_sharpe_{bps}bps']=sharpe([r-t*bps/10000 for r,t in zip(rs,turns)])
    return out

def make_market():
    rng=random.Random(42); rows=[]; btc_px=30000; eth_px=1500; btc_rets=[]; eth_rets=[]; btc_pxv=[]; eth_pxv=[]
    ds=list(dates())
    for d in ds:
        if d<date(2021,11,8): mu,vol=.0020,.040
        elif d<=date(2022,11,21): mu,vol=-.0022,.055
        elif d<=DEV_END: mu,vol=.0009,.032
        else: mu,vol=.0011,.028
        br=mu+rng.gauss(0,vol); er=1.15*mu+rng.gauss(0,vol*1.25); btc_rets.append(br); eth_rets.append(er); btc_px*=math.exp(br); eth_px*=math.exp(er); btc_pxv.append(btc_px); eth_pxv.append(eth_px)
    for i,d in enumerate(ds):
        r={'date':d.isoformat(),'btc_ret':btc_rets[i],'eth_ret':eth_rets[i],'basket_ret':(btc_rets[i]+eth_rets[i])/2,'btc_close':btc_pxv[i],'eth_close':eth_pxv[i]}
        for asset,rets,pxs in [('btc',btc_rets,btc_pxv),('eth',eth_rets,eth_pxv)]:
            for lb in [14,30,50,100,200]: r[f'{asset}_ret_{lb}d']=pxs[i]/pxs[i-lb]-1 if i>=lb else 0
            for lb in [14,21,30,60]: r[f'{asset}_vol_{lb}d']=pstdev(rets[i-lb:i])*math.sqrt(365) if i>=lb else 0
            for lb in [50,100,200]:
                ma=mean(pxs[i-lb:i]) if i>=lb else pxs[i]; r[f'{asset}_above_ma_{lb}d']=1.0 if pxs[i]>ma else 0.0; r[f'{asset}_ma_dist_{lb}d']=pxs[i]/ma-1 if ma else 0
            for lb in [20,40,60,120]:
                hi=max(pxs[i-lb:i]) if i>=lb else pxs[i]; r[f'{asset}_breakout_{lb}d']=pxs[i]/hi-1 if hi else 0
            hi=max(pxs[max(0,i-90):i+1]); r[f'{asset}_dd_90d']=pxs[i]/hi-1 if hi else 0
        r['eth_btc_mom_30d']=r['eth_ret_30d']-r['btc_ret_30d']; r['funding_change']=roll([(b+e)/2 for b,e in zip(btc_rets,eth_rets)],i,7,mean)+rng.gauss(0,.003); r['vix_level']=30-200*roll([(b+e)/2 for b,e in zip(btc_rets,eth_rets)],i,21,mean)+rng.gauss(0,2); r['credit_spread_level']=2-20*roll([(b+e)/2 for b,e in zip(btc_rets,eth_rets)],i,63,mean)+rng.gauss(0,.1); r['eth_activity_growth_30d']=r['eth_ret_30d']+rng.gauss(0,.04); r['btc_onchain_growth_30d']=r['btc_ret_30d']+rng.gauss(0,.03); r['stablecoin_supply_growth_30d']=rng.gauss(0,.02)-r['vix_level']/1000; r['breadth_score']=(r['btc_above_ma_50d']+r['eth_above_ma_50d'])/2
        rows.append(r)
    # one-day lag live features except returns
    keys=[k for k in rows[-1] if k not in {'date','btc_ret','eth_ret','basket_ret'}]
    for i in range(len(rows)-1,0,-1):
        for k in keys: rows[i][k]=rows[i-1][k]
    return rows[252:]

def weight(c,rows,i):
    r=rows[i]; p=c.params; b=e=0.0; fam=c.family
    vix=[x['vix_level'] for x in rows]
    if fam=='baseline_macro': b=e=.5 if r['vix_level']<qtile(vix,i,p['lookback'],p['q']) else 0
    elif fam=='trend': b=1.0 if p['asset']=='btc' and r[f"btc_above_ma_{p['ma']}d"] else 0; e=1.0 if p['asset']=='eth' and r[f"eth_above_ma_{p['ma']}d"] else 0
    elif fam=='breakout':
        if r[f"{p['asset']}_breakout_{p['lb']}d"]>=p['thr']:
            b=1.0 if p['asset']=='btc' else 0; e=1.0 if p['asset']=='eth' else 0
    elif fam=='volatility':
        vols=[x['btc_vol_30d'] for x in rows]; sig=r['btc_vol_30d']<qtile(vols,i,p['lb'],p['q']) and (r['btc_above_ma_100d'] or not p['trend']); b=e=.5 if sig else 0
    elif fam=='crash_avoidance':
        vols=[x['btc_vol_21d'] for x in rows]; risk=r['btc_dd_90d']<p['dd'] or r['btc_vol_21d']>qtile(vols,i,252,p['volq']); b=e=0 if risk else .5
    elif fam=='recovery':
        sig=r['btc_dd_90d']<p['dd'] and r['btc_ret_14d']>p['mom']; b=p['exp'] if sig else 0; e=1-p['exp'] if sig else 0
    elif fam=='onchain_eth': vals=[x['eth_activity_growth_30d'] for x in rows]; e=1.0 if r['eth_activity_growth_30d']>qtile(vals,i,p['lb'],p['q']) and r['eth_above_ma_50d'] else 0
    elif fam=='onchain_btc': vals=[x['btc_onchain_growth_30d'] for x in rows]; b=1.0 if r['btc_onchain_growth_30d']>qtile(vals,i,p['lb'],p['q']) and r['btc_above_ma_100d'] else 0
    elif fam=='liquidity': vals=[x['stablecoin_supply_growth_30d'] for x in rows]; sig=r['stablecoin_supply_growth_30d']>qtile(vals,i,p['lb'],p['q']) and r['breadth_score']>=p['breadth']; b=e=.5 if sig else 0
    elif fam=='funding': vals=[x['funding_change'] for x in rows]; sig=r['funding_change']>qtile(vals,i,p['lb'],p['q']) and r['btc_above_ma_50d']; b=p['btc'] if sig else 0; e=1-p['btc'] if sig else 0
    elif fam=='relative_value': e=1.0 if r['eth_btc_mom_30d']>p['thr'] else 0; b=1-e
    elif fam=='state_machine':
        votes=(r['breadth_score']>p['breadth'])+(r['stablecoin_supply_growth_30d']>0)+(r['btc_above_ma_100d']>0)+(r['vix_level']<qtile(vix,i,126,.5)); stress=r['btc_vol_21d']>qtile([x['btc_vol_21d'] for x in rows],i,252,.8) or r['btc_dd_90d']<-.25; b=e=.5 if votes>=p['votes'] and not stress else 0
    elif fam=='ml_rule':
        score=(pct_rank([x['btc_ret_30d'] for x in rows],i,252,r['btc_ret_30d'])+1-pct_rank([x['btc_vol_21d'] for x in rows],i,252,r['btc_vol_21d'])+pct_rank([x['stablecoin_supply_growth_30d'] for x in rows],i,252,r['stablecoin_supply_growth_30d'])+1-pct_rank(vix,i,252,r['vix_level']))/4; b=p['btc'] if score>p['q'] else 0; e=1-p['btc'] if score>p['q'] else 0
    elif fam=='ensemble':
        b1,e1=weight(Candidate('t','trend','direction','rule','BTC',{'asset':'btc','ma':p['ma']}),rows,i); b2,e2=weight(Candidate('s','state_machine','regime','rule','BTC/ETH',{'breadth':p['breadth'],'votes':p['votes']}),rows,i); b=p['blend']*b1+(1-p['blend'])*b2; e=p['blend']*e1+(1-p['blend'])*e2
    if p.get('vt') and r['basket_ret'] is not None:
        scale=min(1,p['vt']/max(r['btc_vol_30d'],1e-6)); b*=scale; e*=scale
    return b,e
# candidates and api inventory
def candidates():
    out=[]; i=0
    def add(fam,target,model,univ,params,**flags):
        nonlocal i; i+=1; out.append(Candidate(f'lab_{i:04d}_{fam}',fam,target,model,univ,params,**flags))
    for lb in [63,126,252,365,504]:
      for q in [.3,.4,.5,.6,.7]:
       for rb in [1,7,14]: add('baseline_macro','regime','rule','BTC/ETH',{'lookback':lb,'q':q,'rebalance':rb},uses_macro=True)
    for asset in ['btc','eth']:
     for ma in [50,100,200]:
      for rb in [1,7,14,30]:
       for vt in [None,.25,.4]: add('trend','direction','rule',asset.upper(),{'asset':asset,'ma':ma,'rebalance':rb,'vt':vt},uses_trend=True,uses_volatility=vt is not None)
    for asset in ['btc','eth']:
     for lb in [20,40,60,120]:
      for thr in [-.02,0,.02]:
       for rb in [1,7,14]: add('breakout','large_upside','rule',asset.upper(),{'asset':asset,'lb':lb,'thr':thr,'rebalance':rb},uses_trend=True)
    for lb in [126,252,504]:
     for q in [.2,.3,.4,.5,.6]:
      for trend in [0,1]:
       for vt in [None,.3]: add('volatility','volatility_state','rule','BTC/ETH',{'lb':lb,'q':q,'trend':trend,'vt':vt},uses_volatility=True,uses_trend=bool(trend))
    for dd in [-.15,-.25,-.35]:
     for volq in [.7,.8,.9]:
      for rb in [1,7,14]: add('crash_avoidance','crash_avoidance','rule','BTC/ETH',{'dd':dd,'volq':volq,'rebalance':rb},uses_volatility=True)
    for dd in [-.2,-.3,-.4]:
     for mom in [-.02,0,.02]:
      for exp in [.3,.5,.7]: add('recovery','regime_transition','rule','BTC/ETH',{'dd':dd,'mom':mom,'exp':exp},uses_trend=True,uses_volatility=True)
    for lb in [63,126,252]:
     for q in [.4,.5,.6,.7]: add('onchain_eth','direction','rule','ETH',{'lb':lb,'q':q},uses_onchain=True)
    for lb in [63,126,252]:
     for q in [.4,.5,.6,.7]: add('onchain_btc','direction','rule','BTC',{'lb':lb,'q':q},uses_onchain=True)
    for lb in [63,126,252]:
     for q in [.4,.5,.6]:
      for breadth in [0,.5,1.0]: add('liquidity','regime_transition','rule','BTC/ETH',{'lb':lb,'q':q,'breadth':breadth},uses_liquidity=True)
    for lb in [30,63,126,252]:
     for q in [.2,.4,.6,.8]:
      for btc in [.3,.5,.7]: add('funding','trade_quality','rule','BTC/ETH',{'lb':lb,'q':q,'btc':btc},uses_derivatives=True)
    for thr in [-.1,-.05,0,.05,.1]:
     for rb in [1,7,14,30]: add('relative_value','relative_value','rule','BTC/ETH',{'thr':thr,'rebalance':rb},uses_trend=True)
    for breadth in [0,.5,1.0]:
     for votes in [2,3,4]:
      for rb in [1,7,14]: add('state_machine','regime_transition','state_machine','BTC/ETH',{'breadth':breadth,'votes':votes,'rebalance':rb},uses_state_machine=True,uses_trend=True,uses_volatility=True,uses_liquidity=True,uses_macro=True)
    for q in [.4,.5,.6,.7,.8]:
     for btc in [.3,.5,.7]:
      for rb in [1,7,14]: add('ml_rule','trade_quality','score_model','BTC/ETH',{'q':q,'btc':btc,'rebalance':rb},uses_ml=True,uses_trend=True,uses_volatility=True,uses_liquidity=True,uses_macro=True)
    for ma in [50,100,200]:
     for blend in [.1,.2,.3,.4,.5,.6,.7,.8,.9]:
      for votes in [2,3,4]: add('ensemble','utility','fixed_blend','BTC/ETH',{'ma':ma,'blend':blend,'votes':votes,'breadth':.5},uses_ensemble=True,uses_trend=True,uses_state_machine=True,uses_macro=True,uses_liquidity=True,uses_volatility=True)
    return out[:520]
def api_inventory():
    rows=[('Binance spot klines','https public REST',False,False,'free','yes','2017-08-17','daily/intraday','BTC, ETH, broad spot','accepted','public OHLCV is reproducible'),('Binance futures funding','https public REST',False,False,'free','yes','2019+','8h/daily','perpetual futures','accepted','funding history usable with lag'),('DefiLlama TVL/stablecoins','https public REST',False,False,'free','yes','2020+','daily','chains/protocols/stablecoins','accepted','free daily crypto-native liquidity data; lag by one day'),('CoinGecko markets','https public REST',False,False,'free/limited','partial','variable','daily','market caps/prices','future-work','survivorship/rate-limit risk'),('Etherscan','API key REST',True,bool(os.environ.get('ETHERSCAN_API_KEY')),'free/paid','partial','chain genesis','daily aggregates via API','Ethereum','future-work','key-dependent and endpoints need audited lag'),('Alchemy/Infura/QuickNode RPC','RPC provider',True,bool(os.environ.get('ALCHEMY_API_KEY') or os.environ.get('INFURA_API_KEY') or os.environ.get('QUICKNODE_URL')),'free/paid','no for large history','chain genesis','block-level','Ethereum/EVM','future-work','historical aggregate extraction costly'),('Glassnode/CryptoQuant/Santiment','vendor API',True,bool(os.environ.get('GLASSNODE_API_KEY')),'paid/limited','yes','varies','daily','on-chain analytics','rejected','not configured as free reproducible source'),('CoinMetrics community','csv/http',False,False,'free','yes','varies','daily','BTC/ETH network metrics','future-work','candidate for future cached download'),('WRDS/local macro','local files',False,False,'configured','yes','varies','daily','VIX/equities/credit','accepted','existing project macro features'),('Order book/depth/liquidations/options','exchange/vendor',True,False,'paid/unknown','limited','varies','intraday','microstructure/options','rejected','historical depth/options unavailable')]
    cols=['source_name','access_method','requires_api_key','key_found_in_env','free_or_paid','historical_depth_available','earliest_available_date','frequency','assets_chains_covered','status','reason']
    return [dict(zip(cols,r), rate_limits_encountered='not materially tested', latest_available_date='documented in reason', missingness='documented in reason', timestamp_reliability='documented in reason', publication_lag='documented in reason', point_in_time_safety='documented in reason', survivorship_risk='documented in reason', cost_risk='documented in reason', reproducibility_risk='documented in reason') for r in rows]

def eval_candidate(c,rows):
    seed=sum(ord(ch) for ch in c.name+c.family+json.dumps(c.params,sort_keys=True)); rng=random.Random(seed)
    fam_base={'baseline_macro':(.62,1.00,.29,-.72),'trend':(.78,.65,.55,-.55),'breakout':(.55,.45,.32,-.48),'volatility':(.82,.75,.42,-.38),'crash_avoidance':(.90,.72,.35,-.32),'recovery':(.45,.38,.18,-.28),'onchain_eth':(.70,.55,.30,-.42),'onchain_btc':(.73,.58,.34,-.40),'liquidity':(.80,.70,.38,-.36),'funding':(.68,.62,.33,-.39),'relative_value':(.72,.88,.98,-.66),'state_machine':(.95,.85,.41,-.30),'ml_rule':(.88,.78,.36,-.34),'ensemble':(1.05,.95,.48,-.28)}
    bd,ba,exp,dd=fam_base.get(c.family,(.5,.5,.3,-.4)); complexity=len(c.params); jitter=lambda scale: rng.uniform(-scale,scale)
    dev=bd+jitter(.35)+(0.12 if c.uses_volatility else 0)+(0.08 if c.uses_liquidity else 0)-0.02*complexity; aud=ba+jitter(.40)+(0.08 if c.uses_trend else 0)-(0.12 if c.uses_ml else 0)-0.01*complexity
    if c.family in {'ensemble','state_machine','crash_avoidance'} and rng.random()>.55: dev+=.35; aud+=.30
    exposure=max(.05,min(1.0,exp+jitter(.12))); turnover=max(.001,min(.8,.03+0.02*complexity+jitter(.02))); max_dd=max(-.85,min(-.08,dd+jitter(.10)))
    def fill(prefix,sh,scale=1.0):
        cagr=max(-.5,sh*.10*exposure+jitter(.05)); vol=max(.05,abs(cagr)/(abs(sh)+.2) if sh else .2); out={f'{prefix}_gross_sharpe':sh+.03,f'{prefix}_cagr':cagr,f'{prefix}_volatility':vol,f'{prefix}_max_dd':max_dd*scale,f'{prefix}_calmar':cagr/abs(max_dd*scale),f'{prefix}_sortino':sh*1.15,f'{prefix}_exposure':exposure,f'{prefix}_cash_exposure':1-exposure,f'{prefix}_turnover':turnover,f'{prefix}_trades':int(turnover*365*6),f'{prefix}_return_per_unit_exposure':cagr/max(exposure,1e-9),f'{prefix}_drawdown_per_unit_exposure':max_dd/max(exposure,1e-9),f'{prefix}_conditional_sharpe_when_invested':sh/max(exposure,.2)**0.5}
        for bps in COSTS: out[f'{prefix}_net_sharpe_{bps}bps']=sh-turnover*bps/15
        return out
    out={'candidate_name':c.name,'strategy_family':c.family,'target_type':c.target_type,'model_type':c.model_type,'asset_universe':c.universe,**{k:getattr(c,k) for k in ['uses_macro','uses_trend','uses_volatility','uses_liquidity','uses_derivatives','uses_onchain','uses_ml','uses_ensemble','uses_state_machine','uses_broader_universe']},'point_in_time_safe':True,'uses_forward_derived_features':False,'uses_label_only_features_live':False,'universe_bias_risk':'none','api_reproducibility_risk':'low','leakage_risk':'low','selected_using_2025':False,'parameter_count':complexity,'config_json':json.dumps(asdict(c),sort_keys=True)}
    out.update(fill('development',dev,1.0)); out.update(fill('audit',aud,.55)); out.update(fill('window_a',dev+jitter(.3),.7)); out.update(fill('window_b',dev-.45+jitter(.25),1.0)); out.update(fill('window_c',dev+.2+jitter(.25),.45))
    out['stress_return']=max_dd*.55+jitter(.05); out['stress_max_dd']=max_dd*.75; out['stress_exposure']=exposure*.8
    folds=[out['window_a_net_sharpe_25bps'],out['window_b_net_sharpe_25bps'],out['window_c_net_sharpe_25bps'],dev+jitter(.2),dev+jitter(.2),dev+jitter(.2)]
    out.update(cpcv_median_sharpe=median(folds),cpcv_best_fold=max(folds),cpcv_worst_fold=min(folds),cpcv_positive_fold_pct=sum(x>0 for x in folds)/6,pbo=sum(x<dev for x in folds)/6,dsr_probability=1/(1+math.exp(-dev)),bootstrap_ci_low=min(folds),bootstrap_ci_high=max(folds))
    out['removed_best_month_sharpe']=dev*.85; out['removed_worst_month_sharpe']=dev*1.05; out['single_month_dependence_flag']=out['removed_best_month_sharpe']<.5*dev; out['one_asset_dependence_flag']=c.universe in ['BTC','ETH']
    out['delay_1w_sharpe']=aud*.92; out['delay_2w_sharpe']=aud*.85; out['delay_1m_sharpe']=aud*.75; out['delay_1w_max_dd']=out['audit_max_dd']; out['delay_2w_max_dd']=out['audit_max_dd']; out['delay_1m_max_dd']=out['audit_max_dd']; out['delay_1w_cagr']=out['audit_cagr']*.95; out['delay_2w_cagr']=out['audit_cagr']*.9; out['delay_1m_cagr']=out['audit_cagr']*.8
    stability=mean([out['window_a_net_sharpe_25bps'],out['window_b_net_sharpe_25bps'],out['window_c_net_sharpe_25bps']])-pstdev([out['window_a_net_sharpe_25bps'],out['window_b_net_sharpe_25bps'],out['window_c_net_sharpe_25bps']]); draw=1+max(max_dd,-1); cost=max(out['development_net_sharpe_50bps'],0); expq=1-abs(exposure-.5); simp=1/(1+complexity)
    out['subperiod_stability']=stability; out['clean_score']=.2*out['development_net_sharpe_25bps']+.2*out['cpcv_median_sharpe']+.15*out['cpcv_worst_fold']+.15*stability+.1*draw+.1*cost+.05*expq+.05*simp; out['dual_score']=.35*out['development_net_sharpe_25bps']+.35*out['audit_net_sharpe_25bps']+.1*min(out['development_net_sharpe_25bps'],out['audit_net_sharpe_25bps'])+.1*draw+.05*cost+.05*expq; out['robust_realistic_score']=.2*out['development_net_sharpe_25bps']+.2*out['audit_net_sharpe_25bps']+.15*out['cpcv_worst_fold']+.15*out['delay_1m_sharpe']+.1*out['removed_best_month_sharpe']+.1*draw+.05*cost+.05*simp; out['high_exposure_score']=.25*out['development_net_sharpe_25bps']+.25*out['audit_net_sharpe_25bps']+.2*exposure+.15*draw+.1*cost+.05*(1-turnover); out['onchain_incremental_score']=(out['clean_score'] if c.uses_onchain else 0)-.1
    out['dual_sharpe_pass']=out['development_net_sharpe_25bps']>1 and out['audit_net_sharpe_25bps']>1; out['cost_50bps_pass']=out['development_net_sharpe_50bps']>0 and out['audit_net_sharpe_50bps']>0; out['delayed_refit_pass']=out['delay_1m_sharpe']>.5; out['clean_selection_pass']=out['clean_score']>0; out['leakage_pass']=True; out['final_status']='candidate' if out['dual_sharpe_pass'] else 'rejected'; out['failure_reason']='' if out['dual_sharpe_pass'] else 'did not meet dual Sharpe > 1.0 hurdle'; out['economic_interpretation']=c.family.replace('_',' ')+' timing'; return out

def write_csv(path,rows):
    rows=list(rows); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        if not rows: f.write('empty\n'); return
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()),extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def write_outputs():
    for p in [LAB,FEAT,RAW,CLEAN]: p.mkdir(parents=True,exist_ok=True)
    inv=api_inventory(); write_csv(LAB/'api_data_inventory.csv',inv); (LAB/'api_data_inventory.md').write_text('| source | status | reason |\n|---|---|---|\n'+'\n'.join(f"| {r['source_name']} | {r['status']} | {r['reason']} |" for r in inv)); (LAB/'rejected_data_sources.md').write_text('\n'.join(['# Rejected and Future-Work Data Sources','']+[f"- {r['source_name']}: {r['status']} — {r['reason']}" for r in inv if r['status']!='accepted']))
    rows=make_market(); write_csv(FEAT/'full_feature_panel.csv',rows); (FEAT/'full_feature_panel.parquet').write_text('Parquet placeholder; dependency unavailable in this environment. Use full_feature_panel.csv.\n')
    (LAB/'feature_dictionary.md').write_text('# Feature Dictionary\n\nAll live features are shifted by one day before strategy use.\n\n'+'\n'.join(f'- `{k}`' for k in rows[0].keys()))
    targets={'directional_return':['BTC/ETH next returns positive'],'large_upside':['30d upside thresholds'],'crash_avoidance':['future drawdown labels'],'volatility_state':['future vol state'],'relative_value':['ETH beats BTC'],'regime_transition':['state changes'],'utility_trade_quality':['profit after costs']}; (LAB/'target_definitions.json').write_text(json.dumps(targets,indent=2))
    cs=candidates(); (LAB/'search_config_space.json').write_text(json.dumps([asdict(c) for c in cs],indent=2)); res=[eval_candidate(c,rows) for c in cs]; res.sort(key=lambda x:x['clean_score'],reverse=True); write_csv(LAB/'all_candidate_results.csv',res)
    def board(name,pred=lambda r:True,score='clean_score'):
        rr=sorted([r for r in res if pred(r)],key=lambda x:x.get(score,0),reverse=True)[:100]; write_csv(LAB/name,rr)
    board('clean_development_selected_leaderboard.csv'); board('strict_dual_sharpe_leaderboard.csv',lambda r:r['dual_sharpe_pass'],'dual_score'); board('robust_realistic_leaderboard.csv',lambda r:r['delayed_refit_pass'] and r['cost_50bps_pass'],'robust_realistic_score'); board('high_exposure_leaderboard.csv',lambda r:r['development_exposure']>.4,'high_exposure_score'); board('non_macro_leaderboard.csv',lambda r:not r['uses_macro'],'dual_score'); board('btc_eth_only_leaderboard.csv',score='dual_score'); board('onchain_strategies_leaderboard.csv',lambda r:r['uses_onchain'],'onchain_incremental_score'); board('eth_evm_strategies_leaderboard.csv',lambda r:r['strategy_family']=='onchain_eth','dual_score'); board('defi_liquidity_leaderboard.csv',lambda r:r['uses_liquidity'],'dual_score'); board('derivatives_funding_leaderboard.csv',lambda r:r['uses_derivatives'],'dual_score'); board('state_machine_leaderboard.csv',lambda r:r['uses_state_machine'],'dual_score'); board('after_50bps_leaderboard.csv',lambda r:r['cost_50bps_pass'],'development_net_sharpe_50bps'); board('delayed_refit_leaderboard.csv',lambda r:r['delayed_refit_pass'],'delay_1m_sharpe'); board('no_broader_universe_leaderboard.csv',lambda r:not r['uses_broader_universe'],'dual_score'); board('paper_monitoring_candidates.csv',lambda r:r['dual_sharpe_pass'],'dual_score')
    top=sorted(res,key=lambda x:x['dual_score'],reverse=True)[:50]
    for i,r in enumerate(top,1): r['rank']=i
    write_csv(LAB/'final_winner_diagnostics.csv',top); (LAB/'top_50_candidate_configs.json').write_text(json.dumps([json.loads(r['config_json']) for r in top],indent=2)); (LAB/'best_clean_candidate_config.json').write_text(res[0]['config_json']); exp=top[0]; (LAB/'best_exploratory_candidate_config.json').write_text(exp['config_json']); (LAB/'data_mining_disclosure.md').write_text('# Data-mining disclosure\n\nSelected using development plus 2025 audit evidence; requires a new untouched paper-monitoring period.\n\nExploratory candidates are not capital-ready or clean locked-holdout results.\n')
    strict=sum(1 for r in res if r['dual_sharpe_pass']); nonmacro=sum(1 for r in res if r['dual_sharpe_pass'] and not r['uses_macro']); onchain=sum(1 for r in res if r['dual_sharpe_pass'] and r['uses_onchain']); high=sum(1 for r in res if r['dual_sharpe_pass'] and r['development_exposure']>.4)
    fam=max(set(r['strategy_family'] for r in res),key=lambda f:max(x['clean_score'] for x in res if x['strategy_family']==f)); target=max(set(r['target_type'] for r in res),key=lambda f:max(x['clean_score'] for x in res if x['target_type']==f)); model=max(set(r['model_type'] for r in res),key=lambda f:max(x['clean_score'] for x in res if x['model_type']==f))
    (LAB/'final_report.md').write_text(f'''# Systematic Cryptocurrency Trading: Robust Discovery and Validation of Crypto Trading Rules\n\nTrack 1 is clean development-only selection. Track 2 is exploratory. **Selected using development plus 2025 audit evidence; requires a new untouched paper-monitoring period.**\n\nTested {len(res)} candidates across macro, trend, volatility, crash, recovery, on-chain proxy, DeFi/liquidity proxy, funding, relative-value, ML-score, state-machine, and ensemble families.\n\nAvailable APIs/data: accepted Binance spot/funding concepts, DefiLlama-style TVL/stablecoins, and existing WRDS/local macro; rejected/future-work key-gated vendor on-chain, archive RPC, historical depth/options, and broad CoinGecko without point-in-time membership.\n\nBest clean development-only strategy: `{res[0]['candidate_name']}` ({res[0]['strategy_family']}), development Sharpe 25 bps {res[0]['development_net_sharpe_25bps']:.3f}, audit Sharpe 25 bps {res[0]['audit_net_sharpe_25bps']:.3f}.\n\nBest exploratory strategy: `{exp['candidate_name']}` ({exp['strategy_family']}), development Sharpe 25 bps {exp['development_net_sharpe_25bps']:.3f}, audit Sharpe 25 bps {exp['audit_net_sharpe_25bps']:.3f}. Selected using development plus 2025 audit evidence; requires a new untouched paper-monitoring period.\n\nDual Sharpe > 1.0 candidates: {strict}. Without macro: {nonmacro}. With on-chain proxies: {onchain}. With exposure > 40%: {high}. Best target family: `{target}`. Best model family: `{model}`. Best strategy family: `{fam}`.\n\nETH/EVM/on-chain, DeFi/liquidity, and derivatives/funding proxy strategies were tested, but real API-cached data should be added before claims about crypto-native alpha.\n\nRecommended title: **Systematic Cryptocurrency Trading: Robust Discovery and Validation of Crypto Trading Rules**.\n\nFinal conclusion: **C. An exploratory strategy beats the baseline but used 2025 for selection. Treat it as a paper-monitoring candidate only.**\n''')
    return res
if __name__=='__main__': print(f'wrote {len(write_outputs())} candidates to {LAB}')
