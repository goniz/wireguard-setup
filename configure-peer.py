#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys

def gen_wg_conf(interface_name, server_ip, server_port, server_pubkey, private_key):
    conf_path = f'/etc/wireguard/{interface_name}.conf'
    conf_template = f'''
[Interface]
PrivateKey = {private_key}

[Peer]
PublicKey = {server_pubkey}
Endpoint = {server_ip}:{server_port}
AllowedIPs = 0.0.0.0/0
    '''

    with open(conf_path, 'w') as fp:
        fp.write(conf_template)


def gen_systemd_service(interface_name, interface_ip, interface_mtu, server_ip, default_gw_ip, default_gw_interface):
    systemd_service_path = f'/etc/systemd/system/wireguard-peer-{interface_name}.service'
    systemd_service_template = f'''
[Unit]
Description=WireGuard VPN Peer Service
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes

# Delete the interface if already present, but do not fail if it does not exist
ExecStart=-ip link del dev {interface_name}
# Create the Wireguard interface
ExecStart=ip link add dev {interface_name} type wireguard
# Apply the configuration to the interface
ExecStart=wg setconf {interface_name} /etc/wireguard/{interface_name}.conf
# Add the IP address, set the MTU and bring the interface up
ExecStart=ip addr add {interface_ip}/24 dev {interface_name}
ExecStart=ip link set mtu {interface_mtu} dev {interface_name}
ExecStart=ip link set up dev {interface_name}

ExecStart=-ip route del default dev {default_gw_interface}
ExecStart=ip route add default dev {interface_name}
ExecStart=-ip route del {server_ip}/32 via {default_gw_ip} dev {default_gw_interface}
ExecStart=ip route add {server_ip}/32 via {default_gw_ip} dev {default_gw_interface}


# Remove the interface when the service is stopped
ExecStop=ip link del dev {interface_name}
ExecStop=ip route del {server_ip}/32 via {default_gw_ip} dev {default_gw_interface}
ExecStop=ip route add default via {default_gw_ip} dev {default_gw_interface}
    '''

    with open(systemd_service_path, 'w') as fp:
        fp.write(systemd_service_template)

    subprocess.check_call('systemctl daemon-reload', shell=True)

def start_systemd_service(interface_name):
    subprocess.check_call(f'systemctl start wireguard-peer-{interface_name}.service', shell=True)

def enable_systemd_service(interface_name):
    subprocess.check_call(f'systemctl enable wireguard-peer-{interface_name}.service', shell=True)

def main():
    parser = argparse.ArgumentParser(description='Generate peer configuration')
    parser.add_argument('--server-ip', required=True, help='IP address of the peer')
    parser.add_argument('--server-port', type=int, default=51820, help='Port of the peer')
    parser.add_argument('--server-pubkey', type=str, required=True, help='Public key of the peer')
    parser.add_argument('--interface', type=str, default='wg0', help='Name of the interface')
    parser.add_argument('--interface-ip', type=str, required=True, help='IP address of the interface')
    parser.add_argument('--interface-mtu', type=int, default=1400, help='MTU of the interface')
    parser.add_argument('--private-key', type=str, required=True, help='Private key of the interface')
    parser.add_argument('--default-gw-ip', type=str, required=True, help='IP address of the default gateway')
    parser.add_argument('--default-gw-interface', type=str, required=True, help='Name of the default gateway interface')
    parser.add_argument('--enable-on-startup', action="store_true", help='Whether to enable the systemd service')
    parser.add_argument('--start-now', action="store_true", help='Whether to start the systemd service')
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("This script must be run as root (sudo).")
        sys.exit(1)

    gen_wg_conf(args.interface, args.server_ip, args.server_port, args.server_pubkey, args.private_key)
    gen_systemd_service(args.interface, args.interface_ip, args.interface_mtu, args.server_ip, args.default_gw_ip, args.default_gw_interface)

    if args.start_now:
        start_systemd_service(args.interface)

    if args.enable_on_startup:
        enable_systemd_service(args.interface)


if __name__ == '__main__':
    main()
