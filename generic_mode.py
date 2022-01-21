from generic import load_attack_data, get_attack_id, get_tactics
from constants import *
from textwrap import wrap


def _get_platforms_for_data_source(data_source, domain):
    """
    Get the ATT&CK platforms that apply to the provided data source
    :param data_source: ATT&CK data component or DeTT&CT data source
    :param domain: the specified domain (enterprise or ics)
    :return: list of ATT&CK platforms
    """
    attack_data_sources = DATA_SOURCES_ENTERPRISE if domain == 'enterprise' else DATA_SOURCES_ICS
    dettect_data_sources = DETTECT_DATA_SOURCES_PLATFORMS_ENTERPRISE if domain == 'enterprise' else DETTECT_DATA_SOURCES_PLATFORMS_ICS

    platforms = []
    for platform, data_sources in attack_data_sources.items():
        if data_source in data_sources:
            platforms.append(platform)
    for platform, data_sources in dettect_data_sources.items():
        if data_source in data_sources:
            platforms.append(platform)

    return platforms


def get_statistics_data_sources(domain):
    """
    Print out statistics related to data sources and how many techniques they cover.
    :param domain: the specified domain
    :return:
    """
    stix_type = DATA_TYPE_STIX_ALL_TECH_ENTERPRISE if domain == 'enterprise' else DATA_TYPE_STIX_ALL_TECH_ICS
    techniques = load_attack_data(stix_type)

    # {data_source: {techniques: [T0001, ...], count: ..., platforms: []}
    data_sources_dict = {}
    for tech in techniques:
        tech_id = tech['technique_id']
        # Not every technique has a data source listed
        data_sources = tech.get('x_mitre_data_sources', [])
        dettect_data_sources = tech.get('dettect_data_sources', [])
        for ds in data_sources + dettect_data_sources:
            if ds not in data_sources_dict:
                ds_component = ds
                if ':' in ds:
                    ds_component = ds.split(':')[1][1:].lstrip().rstrip()
                platforms = _get_platforms_for_data_source(ds_component, domain)
                data_sources_dict[ds] = {'techniques': [tech_id], 'count': 1, 'platforms': platforms}
            else:
                data_sources_dict[ds]['techniques'].append(tech_id)
                data_sources_dict[ds]['count'] += 1

    # sort the dict on the value of 'count'
    data_sources_dict_sorted = dict(sorted(data_sources_dict.items(), key=lambda kv: kv[1]['count'], reverse=True))
    str_format = '{:<6s} {:<40s} {:s}'
    print(str_format.format('Count', 'Data Source', 'Platform(s)'))
    print('-' * 120)
    for k, v in data_sources_dict_sorted.items():
        data_source = k
        if ':' in k:
            data_source = k.split(':')[1][1:].lstrip().rstrip()

        platforms = ', '.join(v['platforms'])
        platforms = wrap(platforms, 70, break_long_words=False)

        print(str_format.format(str(v['count']), data_source, platforms[0]))
        for p in platforms[1:]:
            print(' ' * 48 + p)


def get_statistics_mitigations(domain):
    """
    Print out statistics related to mitigations and how many techniques they cover
    :param domain: the specified domain
    :return:
    """

    if domain == 'enterprise':
        mitigations = load_attack_data(DATA_TYPE_STIX_ALL_ENTERPRISE_MITIGATIONS)
    elif domain == 'mobile':
        mitigations = load_attack_data(DATA_TYPE_STIX_ALL_MOBILE_MITIGATIONS)
    elif domain == 'ics':
        mitigations = load_attack_data(DATA_TYPE_STIX_ALL_ICS_MITIGATIONS)

    mitigations_dict = dict()
    for m in mitigations:
        if m['external_references'][0]['external_id'].startswith('M'):
            mitigations_dict[m['id']] = {'mID': m['external_references'][0]['external_id'], 'name': m['name']}

    relationships = load_attack_data(DATA_TYPE_STIX_ALL_RELATIONSHIPS)
    relationships_mitigates = [r for r in relationships
                               if r['relationship_type'] == 'mitigates'
                               if r['source_ref'].startswith('course-of-action')
                               if r['target_ref'].startswith('attack-pattern')
                               if r['source_ref'] in mitigations_dict]

    # {id: {name: ..., count: ..., name: ...} }
    count_dict = dict()
    for r in relationships_mitigates:
        src_ref = r['source_ref']

        m = mitigations_dict[src_ref]
        if m['mID'] not in count_dict:
            count_dict[m['mID']] = dict()
            count_dict[m['mID']]['count'] = 1
            count_dict[m['mID']]['name'] = m['name']
        else:
            count_dict[m['mID']]['count'] += 1

    count_dict_sorted = dict(sorted(count_dict.items(), key=lambda kv: kv[1]['count'], reverse=True))

    str_format = '{:<6s} {:<14s} {:s}'
    print(str_format.format('Count', 'Mitigation ID', 'Name'))
    print('-' * 60)
    for k, v in count_dict_sorted.items():
        print(str_format.format(str(v['count']), k, v['name']))


def get_updates(update_type, sort='modified'):
    """
    Print a list of updates for a techniques, groups or software. Sort by modified or creation date.
    :param update_type: the type of update: techniques, groups or software
    :param sort: sort the list by modified or creation date
    :return:
    """
    from pprint import pprint
    if update_type[: -1] == 'technique':
        techniques = load_attack_data(DATA_TYPE_STIX_ALL_TECH)
        sorted_techniques = sorted(techniques, key=lambda k: k[sort])

        for t in sorted_techniques:

            if t['technique_id'] == None:
                pprint(t)
                quit()

            print(t['technique_id'] + ' ' + t['name'])
            print(' ' * 6 + 'created:  ' + t['created'].strftime('%Y-%m-%d'))
            print(' ' * 6 + 'modified: ' + t['modified'].strftime('%Y-%m-%d'))
            print(' ' * 6 + 'domain:   ' + t['external_references'][0]['source_name'][6:])
            tactics = get_tactics(t)
            if tactics:
                print(' ' * 6 + 'tactic:   ' + ', '.join(tactics))
            else:
                print(' ' * 6 + 'tactic:   None')
            print('')

    elif update_type[: -1] == 'group':
        groups = load_attack_data(DATA_TYPE_STIX_ALL_GROUPS)
        sorted_groups = sorted(groups, key=lambda k: k[sort])

        for g in sorted_groups:
            print(get_attack_id(g) + ' ' + g['name'])
            print(' ' * 6 + 'created:  ' + g['created'].strftime('%Y-%m-%d'))
            print(' ' * 6 + 'modified: ' + g['modified'].strftime('%Y-%m-%d'))
            print('')

    elif update_type == 'software':
        software = load_attack_data(DATA_TYPE_STIX_ALL_SOFTWARE)
        sorted_software = sorted(software, key=lambda k: k[sort])

        for s in sorted_software:
            print(get_attack_id(s) + ' ' + s['name'])
            print(' ' * 6 + 'created:  ' + s['created'].strftime('%Y-%m-%d'))
            print(' ' * 6 + 'modified: ' + s['modified'].strftime('%Y-%m-%d'))
            print(' ' * 6 + 'domain:   ' + s['external_references'][0]['source_name'][6:])
            print(' ' * 6 + 'type:     ' + s['type'])
            if 'x_mitre_platforms' in s:
                print(' ' * 6 + 'platform: ' + ', '.join(s['x_mitre_platforms']))
            else:
                print(' ' * 6 + 'platform: None')
            print('')
