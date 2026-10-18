#!/usr/bin/env python3
"""Independent endpoint-only audit; no simulation, repository imports or services.

Wilson limits are obtained by numerical inversion of the binomial score test,
not by calling either prior validator or production/simulation helpers. The
1e-11 tolerance tests floating-point agreement, not scientific acceptance.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import socket
from statistics import NormalDist


def denied(*args, **kwargs):
    raise RuntimeError('Network/DNS forbidden for preserved-evidence audit')


socket.socket = denied
socket.create_connection = denied
socket.getaddrinfo = denied
Z2 = NormalDist().inv_cdf(.975)**2
TOL = 1e-11


def rate(k, n):
    q = k/n
    def score_gap(p):
        return (k-n*p)**2-Z2*n*p*(1-p)
    def boundary(left, right, lower):
        for _ in range(80):
            mid = (left+right)/2
            if (score_gap(mid)>0) == lower:
                left = mid
            else:
                right = mid
        return (left+right)/2
    return {
        'count': k, 'trials': n, 'rate': q,
        'mc_standard_error': math.sqrt(k*(n-k)/(n**3)),
        'mc_wilson_95_interval': [0.0 if k==0 else boundary(0,q,True),
                                  1.0 if k==n else boundary(q,1,False)],
    }


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(data, root):
    errors=[]
    def compare(actual, expected, label):
        if isinstance(expected, dict):
            if not isinstance(actual, dict) or actual.keys()!=expected.keys():
                errors.append(label+': object fields differ')
                return
            for key in expected:
                compare(actual[key],expected[key],label+'.'+key)
        elif isinstance(expected,list):
            if not isinstance(actual,list) or len(actual)!=len(expected):
                errors.append(label+': array shape differs')
                return
            for i,value in enumerate(expected):
                compare(actual[i],value,label+f'[{i}]')
        elif type(expected) is float:
            if (type(actual) not in (int,float) or not math.isfinite(actual)
                    or not math.isclose(actual,expected,abs_tol=TOL,rel_tol=TOL)):
                errors.append(label+': numerical mismatch')
        elif type(actual) is not type(expected) or actual!=expected:
            errors.append(label+': value/type mismatch')

    source_paths={'implementation_sha256':'src/evals/statistical_evidence.py',
                  'script_sha256':'scripts/calibrate_statistical_interval.py'}
    for field,path in source_paths.items():
        compare(data[field],sha(root/path),field)
    compare(data['status'],'nonconfirmatory_model_free_preparation_not_methodology_approval','status')
    compare(data['implementation'],'src.evals.statistical_evidence.paired_hierarchical_bootstrap','implementation')
    n=data['parameters']['outer_trials_per_scenario']
    if type(n) is not int or n<2:
        raise ValueError('need at least two outer datasets')
    all_seeds=set()
    results=[]
    total=0
    names=set()
    for j,block in enumerate(data['scenarios']):
        scenario=block['scenario']; name=scenario['name']
        if name in names:
            raise ValueError('duplicate scenario')
        names.add(name)
        ps=scenario['baseline_probabilities']; qs=scenario['candidate_probabilities']
        if not ps or len(ps)!=len(qs):
            raise ValueError('unaligned probabilities')
        if any(type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 for p in ps+qs):
            raise ValueError('invalid probability')
        truth=float(sum((Fraction(str(q))-Fraction(str(p)) for p,q in zip(ps,qs)),Fraction())/len(ps))
        compare(block['true_effect'],truth,name+'.true_effect')
        compare(block['target'],'fixed_task_equal_weight_mean_probability_difference',name+'.target')
        if len(block['trials'])!=n:
            raise ValueError('trial count differs')
        widths=[]; estimates=[]; covered=excluded=positive=zero=0
        for i,record in enumerate(block['trials']):
            label=f'{name}.trial[{i}]'
            compare(record['trial'],i,label+'.trial')
            seed=data['parameters']['master_seed']+100000*j+2*i
            for field,expected in [('data_seed',seed),('bootstrap_seed',seed+1)]:
                compare(record[field],expected,label+'.'+field)
                if type(record[field]) is not int or record[field] in all_seeds:
                    errors.append(label+': duplicate/noninteger seed')
                all_seeds.add(record[field])
            ends=record['interval']
            if (not isinstance(ends,list) or len(ends)!=2 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in ends) or
                not -1<=ends[0]<=ends[1]<=1):
                raise ValueError(label+': invalid interval')
            lo,hi=ends
            estimate=record['estimate']
            if type(estimate) not in (int,float) or not math.isfinite(estimate) or not -1<=estimate<=1:
                raise ValueError(label+': invalid estimate')
            # With equal repeats the equal-task estimate lies on this rational lattice.
            denominator=len(ps)*scenario['repeats']
            compare(estimate*denominator,float(round(estimate*denominator)),label+'.estimate_lattice')
            if scenario['dependence']=='paired' and ps==qs:
                compare(estimate,0.0,label+'.identical_arm_estimate')
            width=hi-lo; c=lo<=truth<=hi; e=lo>0 or hi<0; p=lo>0
            for field,expected in [('width',width),('covers_truth',c),('excludes_zero',e),('positive_claim',p)]:
                compare(record[field],expected,label+'.'+field)
            widths.append(width); estimates.append(estimate)
            covered+=c; excluded+=e; positive+=p; zero+=width==0; total+=1
        average=math.fsum(widths)/n
        se=math.sqrt(math.fsum((x-average)**2 for x in widths)/(n*(n-1)))
        summary={
            'coverage':rate(covered,n),
            'two_sided_null_false_positive':rate(excluded,n) if truth==0 else None,
            'positive_null_false_positive':rate(positive,n) if truth==0 else None,
            'zero_exclusion_rate':rate(excluded,n),
            'mean_width':average,'width_mc_standard_error':se,
            'mean_width_mc_normal_95_interval':[average-1.96*se,average+1.96*se],
            'zero_width_count':zero,'mean_estimate':math.fsum(estimates)/n,
        }
        compare(block['summary'],summary,name+'.summary')
        if truth==0 and covered+excluded!=n:
            errors.append(name+': null coverage/exclusion complement fails')
        results.append({'name':name,'true_effect':truth,'tasks':len(ps),
                        'repeats':scenario['repeats'],'dependence':scenario['dependence'],
                        'summary':summary})
    return {'status':'verified_summaries_only_not_method_acceptance' if not errors else 'disagreements',
            'errors':errors,'checked_trials':total,'unique_seeds':len(all_seeds),
            'numeric_agreement_tolerance':TOL,'scenarios':results}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=args.source_root/'experiments/phase4-calibration-20261017/existing-interval-simulation.json'
    files=[source,args.source_root/'src/evals/statistical_evidence.py',
           args.source_root/'scripts/calibrate_statistical_interval.py',
           args.source_root/'scripts/validate_statistical_calibration.py',
           args.source_root/'experiments/phase4-calibration-20261017/independent-summary-validation.json',
           args.source_root/'docs/agent-evaluation-evidence-method.md']
    before={str(p):sha(p) for p in files}
    if before[str(source)]!='81a41a2f31cb28e0480416e63b8eba58d877f3bd866174cf5c794906ca273768':
        raise ValueError('preserved simulation pin differs')
    result=verify(json.loads(source.read_text()),args.source_root)
    result.update({'input_manifest_sha256':before,'verifier_sha256':sha(Path(__file__)),
                   'python_version':platform.python_version(),'network_and_dns_denied':True,
                   'preserved_files_unchanged':all(sha(Path(p))==h for p,h in before.items()),
                   'raw_scope':{'stored_endpoint_records':result['checked_trials'],
                                'raw_boolean_matrices_stored':False,'bootstrap_draw_arrays_stored':False,
                                'new_simulations':0,'bootstrap_endpoint_replays':0,'point_estimate_replays':0},
                   'claim_boundary':'Endpoint arithmetic and summary verification only. No bootstrap endpoints independently regenerated; no method selection, scientific acceptance, model inference, database/held-out access or phase advancement.'})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:
        f.write(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['status','checked_trials','unique_seeds','errors','preserved_files_unchanged']}))
    raise SystemExit(bool(result['errors']) or not result['preserved_files_unchanged'])


if __name__=='__main__':
    main()
