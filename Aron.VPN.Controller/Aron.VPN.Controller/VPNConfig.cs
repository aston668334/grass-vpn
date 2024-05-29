using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Aron.VPN.Controller
{
    public class VPNConfig
    {

        public string VPN_NAME { get; set; } = "vpn1";

        public string? VPN_HOST { get; set; }

        public int? VPN_PORT { get; set; }


        public string? VPN_HUB { get; set; }

        public string? VPN_USER { get; set; }

        public string? VPN_PASSWORD { get; set; }

        public string? VPN_NIC_MAC { get; set; }


    }
}
