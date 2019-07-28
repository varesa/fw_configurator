import yaml


def read_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)


def belongs_to_group(y, zone, group):
    assert group in y.zone_groups.keys()
    if 'include' in y.zone_groups[group].keys():
        return zone in y.zone_groups[group].include
    elif 'exclude' in y.zone_groups[group].keys():
        return zone not in y.zone_groups[group].exclude
    else:
        assert f"Do not know what to do with group {group}"


def belongs_to(zone, selector):
    if selector == "from-any" or selector == "to-any":
        return True
    if selector.startswith('to-group-') or selector.startswith('from-group-'):
        group_name = selector.split('-', maxsplit=2)[2]
        return belongs_to_group(zone, group_name)
    if selector == f"to-{zone}" or selector == f"from-{zone}":
        return True
    return False


def make_comment(source, destination):
    if source == 'from-any':
        source = 'Any'
    elif source.startswith('from-group-'):
        source = f"Group {source[11:]}"
    else:
        source = f"Zone {source[5:]}"

    if destination == 'to-any':
        destination = 'Any'
    elif destination.startswith('to-group-'):
        destination = f"Group {destination[9:]}"
    else:
        destination = f"Zone {destination[3:]}"

    return f"{source} to {destination}"


def quoted_last(input):
    split = input.split(' ')
    if not split[-1].startswith("'"):
        split[-1] = f"'{split[-1]}'"
    return ' '.join(split)


def vyos_rule(rule, prefix, source, destination):
    commands = []

    assert isinstance(rule, dict), "vyos_rule must be used with a dict"
    assert isinstance(prefix, str), "vyos_rule must be called with a prefix (firewall name <name>)"
    assert 'id' in rule.keys(), "rule must have an id"

    action = rule['action'] if 'action' in rule.keys() else 'accept'

    commands.append(f"{prefix} rule {rule['id']} action '{action}'")

    if 'source' in rule.keys():
        commands.append(f"{prefix} rule {rule['id']} source {quoted_last(rule['source'])}")

    if 'destination' in rule.keys():
        commands.append(f"{prefix} rule {rule['id']} destination {quoted_last(rule['destination'])}")

    if 'port' in rule.keys():
        commands.append(f"{prefix} rule {rule['id']} destination port '{rule['port']}'")

    if 'portgroup' in rule.keys():
        commands.append(f"{prefix} rule {rule['id']} destination group port-group '{rule['portgroup']}'")

    if 'proto' in rule.keys():
        commands.append(f"{prefix} rule {rule['id']} protocol '{rule['proto']}'")

    if 'extras' in rule.keys():
        for extra in rule['extras']:
            commands.append(f"{prefix} rule {rule['id']} {extra}")

    base_comment = make_comment(source, destination)
    if 'comment' in rule.keys():
        base_comment += rule['comment']
    assert '"' not in base_comment, "Double quotes not allowed in comment"
    assert "'" not in base_comment, "Single quotes not allowed in comment"
    commands.append(f"{prefix} rule {rule['id']} description '{base_comment}'")

    return commands
