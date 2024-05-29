using Microsoft.Extensions.Configuration;
using System.Diagnostics;

namespace Aron.VPN.Controller
{
    internal class Program
    {
        
        static void Main(string[] args)
        {
            IConfiguration Configuration = new ConfigurationBuilder()
                .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
                .AddEnvironmentVariables()
                .AddCommandLine(args)
                .Build();

            var vpnConfig = new VPNConfig();
            Configuration.Bind(vpnConfig);


            ProcessStartInfo startInfo = new ProcessStartInfo
            {
                FileName = "/opt/vpnclient/vpnclient",
                Arguments = $"start",
                RedirectStandardOutput = false,
                RedirectStandardError = false,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process process = Process.Start(startInfo);
            process.Start();
            process.WaitForExit();
            process.Dispose();

            Action action = new Action(vpnConfig);
            action.Start().GetAwaiter().GetResult();

            Thread.Sleep(30000);
            

            while (true)
            {
                Thread.Sleep(60000);
                // run curl -4 ifconfig.me
                //Process curl = new Process()
                //{
                //    StartInfo = new ProcessStartInfo
                //    {
                //        FileName = "/usr/bin/curl",
                //        Arguments = "-4 ifconfig.me",
                //        RedirectStandardOutput = true,
                //        UseShellExecute = false,
                //        CreateNoWindow = true,
                //    }
                //};
                //curl.Start();
                //curl.WaitForExit();
                //curl.Dispose();

                //string output = curl.StandardOutput.ReadToEnd();

                //Console.WriteLine("curl -4 ifconfig.me: " + output);                //Process curl = new Process()
                //{
                //    StartInfo = new ProcessStartInfo
                //    {
                //        FileName = "/usr/bin/curl",
                //        Arguments = "-4 ifconfig.me",
                //        RedirectStandardOutput = true,
                //        UseShellExecute = false,
                //        CreateNoWindow = true,
                //    }
                //};
                //curl.Start();
                //curl.WaitForExit();
                //curl.Dispose();

                //string output = curl.StandardOutput.ReadToEnd();

                //Console.WriteLine("curl -4 ifconfig.me: " + output);

                //if(!output.Contains(vpnConfig.VPN_HOST))
                //{
                //    break;
                //}
            }



        }
    }
}
