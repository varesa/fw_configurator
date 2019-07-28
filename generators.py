import yaml

from groups import CommandGroup
from dotdict import dotdict

def read_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)


def generate_interfaces(filename, number):
    y = read_yaml(filename)

    if number == 1:
        vrrp_prio = 200
    elif number == 2:
        vrrp_prio = 100
    else:
        assert False, f"Unsupported configuration: HA index {number}"

    print(vrrp_prio)

    command_groups = []
    
    # Interfaces to remove:
    for intf in y['delete']:
        group = CommandGroup(prefix='', action='delete')
        group.append(f"interfaces ethernet eth0 vif {intf['vlan']}")
        group.append(f"high-availability vrrp group eth0.{intf['vlan']}-10")
        command_groups.append(group)

    # interfaces to configure
    for intf in y['configure']:
        prefix_i = f"interfaces ethernet eth0 vif {intf['vlan']}"
        group_int = CommandGroup(prefix_i)
        group_int.append(f"{prefix_i} address {intf['vrrp_prefix']}.{number}/24")
        group_int.append(f"{prefix_i} description '{intf['description']}'")
        command_groups.append(group_int)

        prefix_h = f"high-availability vrrp group eth0.{intf['vlan']}-10"
        group_ha = CommandGroup(prefix_h)
        group_ha.append(f"{prefix_h} advertise-interval 1")
        group_ha.append(f"{prefix_h} interface eth0.{intf['vlan']}")
        group_ha.append(f"{prefix_h} priority {vrrp_prio}")
        group_ha.append(f"{prefix_h} virtual-address {intf['vip']}")
        group_ha.append(f"{prefix_h} vrid 10")
        command_groups.append(group_ha)

    # Zone-policy
    group = CommandGroup(prefix='zone-policy')
    for intf in y['configure']:
        for intf2 in y['configure']:
            if intf['short'] != intf2['short']:
                group.append(f"zone-policy zone {intf['short']} from {intf2['short']} firewall name {intf2['short']}_TO_{intf['short']}4")
    command_groups.append(group)

    return command_groups


def generate_firewall(filename):
    y = dotdict(read_yaml(filename))

    command_groups = []

    # Firewall groups

    if 'firewall_groups' in y.keys():
        for group_type in y.firewall_groups.keys():
            for group_name in y.firewall_groups[group_type].keys():
                prefix = f"firewall group {group_type}-group {group_name}"
                command_group = CommandGroup(prefix=prefix)
                for value in y.firewall_groups[group_type][group_name]:
                    command_group.append(f"{prefix} {group_type} '{value}'")
                command_groups.append(command_group)

    # Firewall rules
    
    def belongs_to_group(zone, group):
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

    def vyos_rule(rule, prefix, context=None):
        commands = []

        assert isinstance(rule, dict), "vyos_rule must be used with a dict"
        assert isinstance(prefix, str), "vyos_rule must be called with a prefix (firewall name <name>)"
        assert 'id' in rule.keys(), "rule must have an id"

        action = rule['action'] if 'action' in rule.keys() else 'accept'

        commands.append(f"{prefix} rule {rule['id']} action '{action}'")

        if 'source' in rule.keys():
            commands.append(f"{prefix} rule {rule['id']} source '{rule['source']}'")

        if 'destination' in rule.keys():
            commands.append(f"{prefix} rule {rule['id']} destination '{rule['destination']}'")

        if 'port' in rule.keys():
            commands.append(f"{prefix} rule {rule['id']} destination port '{rule['port']}'")

        if 'portgroup' in rule.keys():
            commands.append(f"{prefix} rule {rule['id']} destination group port-group {rule['portgroup']}")

        if 'proto' in rule.keys():
            commands.append(f"{prefix} rule {rule['id']} protocol '{rule['proto']}'")

        if 'extras' in rule.keys():
            for extra in rule['extras']:
                commands.append(f"{prefix} rule {rule['id']} {extra}")

        if 'comment' in rule.keys():
            assert '"' not in rule['comment'], "Double quotes not allowed in comment"
            comment = rule['comment']
            commands.append(f"{prefix} rule {rule['id']} description \"{comment}\"")

        return commands

    for source_zone in y.zones:
        for destination_zone in y.zones:
            
            if source_zone == destination_zone: 
                continue

            prefix = f"firewall name {source_zone}_TO_{destination_zone}4"
            group = CommandGroup(prefix=prefix)

            group.append(f"{prefix} default-action 'reject'")

            for source in y.rules.keys():
                for destination in y.rules[source].keys():
                    if belongs_to(source_zone, source) and belongs_to(destination_zone, destination):
                        for rule in y.rules[source][destination]:
                            for command in vyos_rule(rule, prefix):
                                group.append(command)
            command_groups.append(group)

    return command_groups

