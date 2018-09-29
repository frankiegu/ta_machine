import json,time,datetime,itertools,os
from pprint import pprint
import pandas as pd
import numpy as np
from tqdm import tqdm
pd.options.mode.chained_assignment = None

def main():
    setup_file = 'setup1538182481.txt'
    p,units_list = get_setup(setup_file)
    ite_list = get_iterList(units_list,0.001) 
    raw_df = get_raw(p)

    setup_dict = {
        'file': setup_file,
        'p': p,
        'triplets_list': []
    }

    for item in tqdm(ite_list):
        setup_dict['triplets_list'].append(get_triplets_list(p,raw_df,units_list,item[0],item[1],item[2]))

    write_json(setup_dict)

def get_iterList(units_list,space):
    buyLowest_list = []
    lowest_list = []
    realHighest_list = []
    
    for unit in units_list:
        buyLowest_list.append(unit['buy']['lowest']['price'])
        if unit['buy']['type'] == 'all-bought':
            realHighest_list.append(unit['sell']['realHighest'])
            lowest_list.append(unit['lowest']['price'])
        else:
            realHighest_list.append(None)
            lowest_list.append(None)

    buyLowest_list = [x for x in buyLowest_list if x is not None]
    lowest_list = [x for x in lowest_list if x is not None]
    realHighest_list = [x for x in realHighest_list if x is not None]

    lowest_buyLowest = min(buyLowest_list)
    highest_buyLowest = max(buyLowest_list)
    lowest_lowest = min(lowest_list)
    highest_lowest = max(lowest_list)
    highest_realHighest = max(realHighest_list)

    if highest_lowest > 0:
        highest_lowest = 0
    if highest_buyLowest > 0:
        highest_buyLowest = 0

    target_ite = list(np.arange(0.006,highest_realHighest,space))
    stop_ite = list(np.arange(lowest_lowest,highest_lowest,space))
    buyStop_ite = list(np.arange(lowest_buyLowest,highest_buyLowest,space))

    ite_list = [target_ite,stop_ite,buyStop_ite]
    return list(itertools.product(*ite_list))

def get_iterList2(units_list,space,buyStop):
    lowest_list = []
    realHighest_list = []
    
    for unit in units_list:
        if unit['buy']['type'] == 'all-bought':
            realHighest_list.append(unit['sell']['realHighest'])
            lowest_list.append(unit['lowest']['price'])
        else:
            realHighest_list.append(None)
            lowest_list.append(None)

    lowest_list = [x for x in lowest_list if x is not None]
    realHighest_list = [x for x in realHighest_list if x is not None]

    lowest_lowest = min(lowest_list)
    highest_lowest = max(lowest_list)
    highest_realHighest = max(realHighest_list)

    target_ite = list(np.arange(0.006,highest_realHighest,space))
    stop_ite = list(np.arange(lowest_lowest,highest_lowest,space))
    buyStop_ite = [buyStop]

    ite_list = [target_ite,stop_ite,buyStop_ite]
    return list(itertools.product(*ite_list))

def get_triplets_list(p,raw_df,units_list,target,stop,buyStop):
    setup = {
        'events': {},
        'info': {
            'target': target,
            'stop': stop,
            'buyStop': buyStop,
        }
    }
    aux_list = []
    for unit in units_list:
        if unit['buy']['lowest']['price'] <= buyStop:
            whether_stopped = 'T' # stopped
        else: 
            whether_stopped = 'F' # not-stopped

        if unit['buy']['type'] == 'all-bought':
            if unit['sell']['realHighest'] >= target and unit['lowest']['price'] > stop:
                partition = 'W' # winner
            if unit['sell']['realHighest'] < target and unit['lowest']['price'] > stop:
                partition = 'C' # consolidation
            if unit['sell']['realHighest'] < target and unit['lowest']['price'] <= stop:
                partition = 'L' # loser
            if unit['sell']['realHighest'] >= target and unit['lowest']['price'] <= stop:
                target_price = unit['buy']['price']*(1+target)
                stop_price = unit['buy']['price']*(1+stop)
                start_index = unit['buy']['last_executed']['index'] + 1
                end_index = unit['sell']['last_executed']['index']
                raw_section = raw_df.loc[start_index:end_index] 
                over_target_df = raw_section[raw_section.price>=target_price]
                over_target_df['acc_volume'] = over_target_df['volume'].cumsum(axis = 0)
                if (over_target_df.acc_volume >= float(p['unit_maker']['max_order'])).any():
                    last_target_index = over_target_df[over_target_df.acc_volume >= float(p['unit_maker']['max_order'])].iloc[0].name
                    first_stop_index = raw_section[raw_section.price <= stop_price].iloc[0].name
                    if last_target_index > first_stop_index:
                        partition = 'L' # loser
                    else:
                        partition = 'W' # winner
                else:
                    partition = 'L' # loser
        if unit['buy']['type'] == 'nothing-bought':
            partition = 'N' # nothing-bought
        if unit['buy']['type'] == 'partially-bought':
            partition = 'P' # partiallly-bought

        aux_list.append(whether_stopped + partition)

    for key in set(aux_list):
        setup['events'][key] = aux_list.count(key)

    return setup

def write_json(data):
    # It dumps the data in a new file called "experiment<ts_now>.txt" in experiment_data directory.
    half1_path = 'builders/warehouse/setup_data/setup_events'
    half2_path = str(int(time.time()))
    path = half1_path + half2_path + '.txt'
    while os.path.exists(path):
        time.sleep(1)
        half2_path = str(int(time.time()))
        path = half1_path + half2_path + '.txt'
    with open(path, 'w') as outfile:
        json.dump(data, outfile)

def get_raw(p):
    return pd.read_csv(p['unit_maker']['path_historical_data'], header=None, names=['timestamp','price','volume'])
    
def get_setup(setup_file):
    dir_path = 'builders/warehouse/setup_data/'
    setup_path = dir_path + setup_file
    with open(setup_path) as f:
        return json.load(f)

if __name__ == '__main__':
    time1 = time.time()
    main()
    time2 = time.time()
    print('---------------------------------------')
    print('Runtime: ',time2-time1)
    print('Ran at: ',datetime.datetime.fromtimestamp(time2))