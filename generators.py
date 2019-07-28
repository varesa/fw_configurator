
from groups import CommandGroup
from dotdict import dotdict
from generator_utilities import read_yaml, belongs_to, vyos_rule


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
                group.append(f"zone-policy zone {intf['short']} from {intf2['short']}" +
                             f"firewall name {intf2['short']}_TO_{intf['short']}4")
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

    for source_zone in y.zones:
        for destination_zone in y.zones:

            if source_zone == destination_zone:
                continue

            prefix = f"firewall name {source_zone}_TO_{destination_zone}4"
            group = CommandGroup(prefix=prefix)

            group.append(f"{prefix} default-action 'reject'")

            for source in y.rules.keys():
                for destination in y.rules[source].keys():
                    if belongs_to(y, source_zone, source) and belongs_to(y, destination_zone, destination):
                        for rule in y.rules[source][destination]:
                            for command in vyos_rule(rule, prefix, source, destination):
                                group.append(command)
            command_groups.append(group)

    return command_groups
