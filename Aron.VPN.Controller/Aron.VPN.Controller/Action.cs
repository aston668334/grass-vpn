using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.NetworkInformation;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using SoftEtherVPNCmdNETCore.VPNClient;
using System.Diagnostics;

namespace Aron.VPN.Controller
{
    public class Action
    {
        private readonly string nicName = "VPN100";
        private string ethName => "vpn_" + nicName.ToLower();

        private VPNConfig vpnConfig;

        private SoftEtherVPNCmdNETCore.VPNClient.VpnClient vpnClient;

        public string VPNNicIp { get; set;}

        public Action(VPNConfig vpnConfig, string vpncmdPath = "/opt/vpnclient/vpncmd")
        {
            this.vpnConfig = vpnConfig;
            vpnClient = new VpnClient(vpncmdPath);
        }

        public async Task Start()
        {
            Console.WriteLine("-----------Create VPN------------");
            await CreateVPN();
            Console.WriteLine("-----------Create VPN End------------\n\n");
            Console.WriteLine("-----------Connect VPN------------");
            await ConnectVPN();
            Console.WriteLine("-----------Connect VPN End------------\n\n");

            Console.WriteLine("-----------Set Nic Mac------------");

            if(!string.IsNullOrEmpty(vpnConfig.VPN_NIC_MAC))
                SetNicMAC(vpnConfig.VPN_NIC_MAC);
            Console.WriteLine("-----------Set Nic Mac End------------\n\n");

            Console.WriteLine("-----------DHCP------------");
            DHCP();
            Console.WriteLine("-----------DHCP End------------\n\n");

            Console.WriteLine("-----------Config DNS------------");
            ConfigDNS();
            Console.WriteLine("-----------Config DNS End------------\n\n");

            Console.WriteLine("-----------Config Route------------");
            ConfigRoute();
            Console.WriteLine("-----------Config Route End------------\n\n");
        }

        public async Task CreateVPN()
        {
            await vpnClient.NicCreate(nicName);

            
            await vpnClient.AccountCreate(vpnConfig.VPN_NAME, $"{vpnConfig.VPN_HOST}:{vpnConfig.VPN_PORT}", vpnConfig.VPN_HUB, vpnConfig.VPN_USER, nicName);

            await vpnClient.AccountPasswordSet(vpnConfig.VPN_NAME, vpnConfig.VPN_PASSWORD, AuthenticationType.Standard);

            await vpnClient.AccountStartupSet(vpnConfig.VPN_NAME);
        }

        public async Task ConnectVPN()
        {
            await vpnClient.AccountConnect(vpnConfig.VPN_NAME);

            Process process = new Process()
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "/usr/bin/lsattr",
                    Arguments = "/etc/resolv.conf",
                    RedirectStandardOutput = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }
            };
            process.Start();
            process.WaitForExit();
            process.Dispose();

            Thread.Sleep(1000);


            SpinWait.SpinUntil(() =>
            {
                Thread.Sleep(1000);
                var accountList = vpnClient.AccountList().GetAwaiter().GetResult();
                return accountList.Any(x => x.VPNConnectionSettingName == vpnConfig.VPN_NAME && x.Status == AccountStatus.Connected);
            }, 30000);
            Thread.Sleep(1000);
        }

        public async Task DisconnectVPN()
        {
            await vpnClient.AccountDisconnect(vpnConfig.VPN_NAME);
        }

        public async Task DeleteVPN()
        {
            await vpnClient.AccountDelete(vpnConfig.VPN_NAME);
            await vpnClient.NicDelete(nicName);
        }


        public void SetNicMAC(string mac)
        {
            Process process = new Process()
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "/sbin/ip",
                    Arguments = $"link set dev {ethName} address {mac}",
                    RedirectStandardOutput = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }
            };
            process.Start();
            process.WaitForExit();
            process.Dispose();
        }

        public void DHCP()
        {
            Thread.Sleep(20000);
            Process process = new Process()
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "/sbin/dhclient",
                    Arguments = ethName,
                    RedirectStandardOutput = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }
            };
            process.Start();
            process.WaitForExit();
            process.Dispose();
            Thread.Sleep(5000);
        }



        public void ConfigDNS()
        {
            //edit /etc/resolv.conf to add nameserver 8.8.8.8, 4.4.4.4
            //get 
            List<string> lines = new() { "options ndots:0", "nameserver 8.8.8.8", "nameserver 4.4.4.4" };
            File.WriteAllLines("/etc/resolv.conf", lines);
        }

        public void ConfigRoute()
        {
            // Get VPN Host IP
            string vpnHost = vpnConfig.VPN_HOST;
            if (!IPAddress.TryParse(vpnHost, out _))
            {
                vpnHost = Dns.GetHostAddresses(vpnHost).First().ToString();
            }
            Console.WriteLine("VPN IP: " + vpnHost);
            VPNNicIp = vpnHost;

            if (string.IsNullOrEmpty(GetVPNDefaultGateway()))
            {
                Console.WriteLine("VPN Gateway is empty");
                Process.GetCurrentProcess().Kill();
            }

            Process process = new Process()
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "/sbin/ip",
                    Arguments = $"route add {vpnHost}/32 via {GetDefaultGateway("eth0")} dev eth0"
                }
            };
            Console.WriteLine(process.StartInfo.Arguments);

            process.Start();
            process.WaitForExit();
            process.Dispose();

            process = new Process()
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "/sbin/ip",
                    Arguments = $"route del default"
                }
            };
            Console.WriteLine(process.StartInfo.Arguments);

            process.Start();
            process.WaitForExit();
            process.Dispose();

            process = new Process()
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "/sbin/ip",
                    Arguments = $"route add default via {GetVPNDefaultGateway()} dev {ethName} metric 100"
                }
            };
            Console.WriteLine(process.StartInfo.Arguments);



            process.Start();
            process.WaitForExit();
            process.Dispose();
        }

        public static string? GetVPNDefaultGateway()
        {
            string content = File.ReadAllText("/var/lib/dhcp/dhclient.leases");
            string pattern = @"option routers\s+([\d.]+);";
            Match match = Regex.Match(content, pattern);

            if (match.Success)
            {
                string routersAddress = match.Groups[1].Value;
                return routersAddress;
            }
            else
            {
                return null;
            }

        }

        public static IPAddress GetDefaultGateway(string name)
        {
            return NetworkInterface
                .GetAllNetworkInterfaces()
                .Where(x => x.Name == name)
                .Where(n => n.OperationalStatus == OperationalStatus.Up)
                .Where(n => n.NetworkInterfaceType != NetworkInterfaceType.Loopback)
                .SelectMany(n => n.GetIPProperties()?.GatewayAddresses)
                .Select(g => g?.Address)
                .FirstOrDefault(a => a != null);
        }
    }
}
