# Copyright 2018 F5 Networks All rights reserved.
#
# Version v2.0.0

"""Creates BIG-IP"""
COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/'
def Metadata(context, group, storageName, licenseType):
  # SETUP VARIABLES
  ## Template Analytics
  ALLOWUSAGEANALYTICS = context.properties['allowUsageAnalytics']
  if ALLOWUSAGEANALYTICS == "yes":
    CUSTHASH = 'CUSTOMERID=`curl -s "http://metadata.google.internal/computeMetadata/v1/project/numeric-project-id" -H "Metadata-Flavor: Google" |sha512sum|cut -d " " -f 1`;\nDEPLOYMENTID=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/id" -H "Metadata-Flavor: Google"|sha512sum|cut -d " " -f 1`;'
    SENDANALYTICS = ' --metrics "cloudName:google,region:' + context.properties['region'] + ',bigipVersion:' + context.properties['imageName'] + ',customerId:${CUSTOMERID},deploymentId:${DEPLOYMENTID},templateName:f5-prod-stack-same-net-cluster-payg-3nic-bigip.py,templateVersion:v2.0.0,licenseType:payg"'
  else:
    CUSTHASH = '# No template analytics'
    SENDANALYTICS = ''
  ## PREFIX
  DOTMASK = 'dotmask=`prefix2mask ' + context.properties['mask1'] + '`'
  DOTMASK2 = 'dotmask2=`prefix2mask ' + context.properties['mask2'] + '`'
  ## Service Discovery
  USESD = 'useServiceDiscovery=\'' + context.properties['tagValue'] + '\''
  SDAPP = '   \'tmsh create /sys application service serviceDiscovery template f5.service_discovery variables add { basic__advanced { value no } basic__display_help { value hide } cloud__cloud_provider { value gce }  cloud__gce_region { value \"/#default#\" } monitor_frequency { value 30 } monitor__http_method { value GET } monitor__http_verison { value http11 } monitor__monitor { value \"/#create_new#\"} monitor__response { value \"\" } monitor__uri { value / } pool__interval { value 60 } pool__member_conn_limit { value 0 } pool__member_port { value 80 } pool__pool_to_use { value \"/#create_new#\" } pool__public_private {value private} pool__tag_key { value ' + context.properties['tagName'] + ' } pool__tag_value { value ' + context.properties['tagValue'] + ' } }\')'
  ## Routes
  EXTRT = '\"tmsh create net route ext_rt network ${network}/' + context.properties['mask1'] + ' gw ${GATEWAY}\"'
  INTRT = '\"tmsh create net route int_rt network ${network2}/' + context.properties['mask2'] + ' gw ${GATEWAY2}\"'
  ## Onboard
  if group == "create" and licenseType == "byol":
    LICENSE = '--license '+ context.properties['licenseKey1']
  elif group == "join" and licenseType == "byol":
    LICENSE = '--license ' + context.properties['licenseKey2']
  else:
    LICENSE = ''
  ONBOARDJS = ' '.join ([ "nohup /config/waitThenRun.sh",
                          "f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/onboard.js",
                          "--port 443",
                          "--ssl-port",
                          "'" + context.properties['mgmtGuiPort'] + "'",
                          "--wait-for ADMIN_CREATED",
                          "-o /var/log/cloud/google/onboard.log",
                          "--log-level debug",
                          "--no-reboot",
                          "--host localhost",
                          "--user admin",
                          "--password-url file:///config/cloud/gce/.adminPassword",
                          "--password-encrypted",
                          "--hostname $(curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/hostname\" -H \"Metadata-Flavor: Google\")",
                          "--ntp 0.us.pool.ntp.org",
                          "--ntp 1.us.pool.ntp.org",
                          "--tz UTC",
                          "--module ltm:nominal",
                          LICENSE + SENDANALYTICS,
                          "&>> /var/log/cloud/google/install.log < /dev/null &"
                        ])
  ## Cluster
  if group == "create":
    CLUSTERJS = ' '.join(["HOSTNAME=$(curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/hostname\" -H \"Metadata-Flavor: Google\");INT2ADDRESS=$(curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/2/ip\" -H \"Metadata-Flavor: Google\");nohup /config/waitThenRun.sh",
                          "f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/cluster.js",
                          "--wait-for CUSTOM_CONFIG_DONE",
                          "--signal CLUSTER_DONE",
                          "-o /var/log/cloud/google/cluster.log",
                          "--log-level silly",
                          "--host localhost",
                          "--user admin",
                          "--password-url file:///config/cloud/gce/.adminPassword",
                          "--password-encrypted",
                          "--cloud gce",
                          "--provider-options 'region:" + context.properties['region'] + ",storageBucket:" + storageName  + "'",
                          "--master",
                          "--config-sync-ip ${INT2ADDRESS}",
                          "--create-group",
                          "--device-group failover_group",
                          "--sync-type sync-failover",
                          "--network-failover",
                          "--device ${HOSTNAME}",
                          "--auto-sync",
                          "&>> /var/log/cloud/google/install.log < /dev/null &"
    ])
  elif group == "join":
    CLUSTERJS = ' '.join(["INT2ADDRESS=$(curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/2/ip\" -H \"Metadata-Flavor: Google\");nohup /config/waitThenRun.sh",
                          "f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/cluster.js",
                          "--wait-for CUSTOM_CONFIG_DONE",
                          "--signal CLUSTER_DONE",
                          "-o /var/log/cloud/google/cluster.log",
                          "--log-level silly",
                          "--host localhost",
                          "--user admin",
                          "--password-url file:///config/cloud/gce/.adminPassword",
                          "--password-encrypted",
                          "--cloud gce",
                          "--provider-options 'region:" + context.properties['region'] + ",storageBucket:" + storageName  + "'",
                          "--config-sync-ip ${INT2ADDRESS}",
                          "--join-group",
                          "--device-group failover_group",
                          "--remote-host ",
                          "$(ref.bigip1-" + context.env['deployment'] + ".networkInterfaces[0].networkIP)",
                          "&>> /var/log/cloud/google/install.log < /dev/null &"
    ])
  else:
    CLUSTERJS = ''

  ## generate metadata
  metadata = {
            'items': [{
                'key': 'startup-script',
                'value': ('\n'.join(['#!/bin/bash',
                                    'if [ -f /config/startupFinished ]; then',
                                    '    exit',
                                    'fi',
                                    'mkdir -p /config/cloud/gce',
                                    'cat <<\'EOF\' > /config/installCloudLibs.sh',
                                    '#!/bin/bash',
                                    'echo about to execute',
                                    'checks=0',
                                    'while [ $checks -lt 120 ]; do echo checking mcpd',
                                    '    tmsh -a show sys mcp-state field-fmt | grep -q running',
                                    '    if [ $? == 0 ]; then',
                                    '        echo mcpd ready',
                                    '        break',
                                    '    fi',
                                    '    echo mcpd not ready yet',
                                    '    let checks=checks+1',
                                    '    sleep 10',
                                    'done',
                                    'echo loading verifyHash script',
                                    'if ! tmsh load sys config merge file /config/verifyHash; then',
                                    '    echo cannot validate signature of /config/verifyHash',
                                    '    exit',
                                    'fi',
                                    'echo loaded verifyHash',
                                    'declare -a filesToVerify=(\"/config/cloud/f5-cloud-libs.tar.gz\" \"/config/cloud/f5-cloud-libs-gce.tar.gz\" \"/config/cloud/f5.service_discovery.tmpl\")',
                                    'for fileToVerify in \"${filesToVerify[@]}\"',
                                    'do',
                                    '    echo verifying \"$fileToVerify\"',
                                    '    if ! tmsh run cli script verifyHash \"$fileToVerify\"; then',
                                    '        echo \"$fileToVerify\" is not valid',
                                    '        exit 1',
                                    '    fi',
                                    '    echo verified \"$fileToVerify\"',
                                    'done',
                                    'mkdir -p /config/cloud/gce/node_modules/@f5devcentral',
                                    'echo expanding f5-cloud-libs.tar.gz',
                                    'tar xvfz /config/cloud/f5-cloud-libs.tar.gz -C /config/cloud/gce/node_modules/@f5devcentral',
                                    'echo expanding f5-cloud-libs-gce.tar.gz',
                                    'tar xvfz /config/cloud/f5-cloud-libs-gce.tar.gz -C /config/cloud/gce/node_modules/@f5devcentral',
                                    'touch /config/cloud/cloudLibsReady',
                                    'EOF',
                                    'cat <<\'EOF\' > /config/verifyHash',
                                    'cli script /Common/verifyHash {',
                                    'proc script::run {} {',
                                    '        if {[catch {',
                                    '            set hashes(f5-cloud-libs.tar.gz) 2481d285c33b97ed083f6e48edcfbd1d5f8fb1dea0578f429017706a1829d3625fab6aff8f55fe71b2b5929410110043a17d57179d833f0f51c90fb0f6ff292d',
                                    '            set hashes(f5-cloud-libs-aws.tar.gz) 35361a507a4ef0c8f5205c05d913dbea024f287777e86dccd0c345560a637c106aeab4150af9eafd828929eb7798184e076ea5359e16b4c2d5544cc380800711',
                                    '            set hashes(f5-cloud-libs-azure.tar.gz) def8780b308a7cfea52d524e5ad07121e7091ecb826e01c87bc758c90fee5c25d12a2a4a06dc78ff64cb478a471f8514bde2cd5da19fb427de28598272a978bb',
                                    '            set hashes(f5-cloud-libs-gce.tar.gz) 9d0d8c32909a272cc9a56dad60121916830462ba26c9bb1d731c10f4e33ba7a856520db55016097db2043e27d048027924470a8e68f366de0339a43b7b68b0d6',
                                    '            set hashes(f5-cloud-libs-openstack.tar.gz) 5c83fe6a93a6fceb5a2e8437b5ed8cc9faf4c1621bfc9e6a0779f6c2137b45eab8ae0e7ed745c8cf821b9371245ca29749ca0b7e5663949d77496b8728f4b0f9',
                                    '            set hashes(asm-policy-linux.tar.gz) 63b5c2a51ca09c43bd89af3773bbab87c71a6e7f6ad9410b229b4e0a1c483d46f1a9fff39d9944041b02ee9260724027414de592e99f4c2475415323e18a72e0',
                                    '            set hashes(f5.http.v1.2.0rc4.tmpl) 47c19a83ebfc7bd1e9e9c35f3424945ef8694aa437eedd17b6a387788d4db1396fefe445199b497064d76967b0d50238154190ca0bd73941298fc257df4dc034',
                                    '            set hashes(f5.http.v1.2.0rc6.tmpl) 811b14bffaab5ed0365f0106bb5ce5e4ec22385655ea3ac04de2a39bd9944f51e3714619dae7ca43662c956b5212228858f0592672a2579d4a87769186e2cbfe',
                                    '            set hashes(f5.http.v1.2.0rc7.tmpl) 21f413342e9a7a281a0f0e1301e745aa86af21a697d2e6fdc21dd279734936631e92f34bf1c2d2504c201f56ccd75c5c13baa2fe7653213689ec3c9e27dff77d',
                                    '            set hashes(f5.aws_advanced_ha.v1.3.0rc1.tmpl) 9e55149c010c1d395abdae3c3d2cb83ec13d31ed39424695e88680cf3ed5a013d626b326711d3d40ef2df46b72d414b4cb8e4f445ea0738dcbd25c4c843ac39d',
                                    '            set hashes(f5.aws_advanced_ha.v1.4.0rc1.tmpl) de068455257412a949f1eadccaee8506347e04fd69bfb645001b76f200127668e4a06be2bbb94e10fefc215cfc3665b07945e6d733cbe1a4fa1b88e881590396',
                                    '            set hashes(f5.aws_advanced_ha.v1.4.0rc2.tmpl) 6ab0bffc426df7d31913f9a474b1a07860435e366b07d77b32064acfb2952c1f207beaed77013a15e44d80d74f3253e7cf9fbbe12a90ec7128de6facd097d68f',
                                    '            set hashes(f5.aws_advanced_ha.v1.4.0rc3.tmpl) 2f2339b4bc3a23c9cfd42aae2a6de39ba0658366f25985de2ea53410a745f0f18eedc491b20f4a8dba8db48970096e2efdca7b8efffa1a83a78e5aadf218b134',
                                    '            set hashes(asm-policy.tar.gz) 2d39ec60d006d05d8a1567a1d8aae722419e8b062ad77d6d9a31652971e5e67bc4043d81671ba2a8b12dd229ea46d205144f75374ed4cae58cefa8f9ab6533e6',
                                    '            set hashes(deploy_waf.sh) 1a3a3c6274ab08a7dc2cb73aedc8d2b2a23cd9e0eb06a2e1534b3632f250f1d897056f219d5b35d3eed1207026e89989f754840fd92969c515ae4d829214fb74',
                                    '            set hashes(f5.policy_creator.tmpl) 06539e08d115efafe55aa507ecb4e443e83bdb1f5825a9514954ef6ca56d240ed00c7b5d67bd8f67b815ee9dd46451984701d058c89dae2434c89715d375a620',
                                    '            set hashes(f5.service_discovery.tmpl) 01dc84d4a4be2bc484ab57b771f186f87d4b664e1fb9a073e025b5362ee14d712b970eef4041f794f66286fb1429418aab16e832c89df8a25e02229c68b83de8',
                                    '            set hashes(f5.cloud_logger.v1.0.0.tmpl) 64a0ed3b5e32a037ba4e71d460385fe8b5e1aecc27dc0e8514b511863952e419a89f4a2a43326abb543bba9bc34376afa114ceda950d2c3bd08dab735ff5ad20',
                                    'NEW_LINE',
                                    '            set file_path [lindex $tmsh::argv 1]',
                                    '            set file_name [file tail $file_path]',
                                    'NEW_LINE',
                                    '            if {![info exists hashes($file_name)]} {',
                                    '                tmsh::log err "No hash found for $file_name"',
                                    '                exit 1',
                                    '            }',
                                    'NEW_LINE',
                                    '            set expected_hash $hashes($file_name)',
                                    '            set computed_hash [lindex [exec /usr/bin/openssl dgst -r -sha512 $file_path] 0]',
                                    '            if { $expected_hash eq $computed_hash } {',
                                    '                exit 0',
                                    '            }',
                                    '            tmsh::log err "Hash does not match for $file_path"',
                                    '            exit 1',
                                    '        }]} {',
                                    '            tmsh::log err {Unexpected error in verifyHash}',
                                    '            exit 1',
                                    '        }',
                                    '    }',
                                    '    script-signature rDemf/H1eVNT9zqev0rGMqJMAsDqmxZOsgwl7LuxD0bocfXqCnZyIt5B6e1nAFWJRwI2m4uKeknO58YAoNJo/+HvoG+4ifoAT71d5f0o2JX13kbvb4qEJAdl0nkGjy2j62CeHSl40+XimWzCBn8FA3bFOhfP6kfs/gAo7OhokBbk4YTxa1Y16hI5rf5Z9fS78/Km2Fs55XU18KKwL81lWyA/6by46V2LvmGYc461j8yFGLsaJLOsgJ6HZQBKRyH1ZrVAA5mdqOU7i9P1VsRgvgLhE/WBraHIDz5olowiq5AfiqnRG//Z6Wn4QgZONn4IGPMViPq+f2NxrDHlirfy/A==',
                                    '    signing-key /Common/f5-irule',
                                    '}',
                                    'EOF',
                                    '# empty new line chars get stripped, strip out place holder NEW_LINE',
                                    'sed -i "s/NEW_LINE//" /config/verifyHash',
                                    'cat <<\'EOF\' > /config/waitThenRun.sh',
                                    '#!/bin/bash',
                                    'while true; do echo \"waiting for cloud libs install to complete\"',
                                    '    if [ -f /config/cloud/cloudLibsReady ]; then',
                                    '        break',
                                    '    else',
                                    '        sleep 10',
                                    '    fi',
                                    'done',
                                    '\"$@\"',
                                    'EOF',
                                    'cat <<\'EOF\' > /config/cloud/gce/custom-config.sh',
                                    '#!/bin/bash',
                                    'HOSTNAME=$(curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/hostname\" -H \"Metadata-Flavor: Google\")',
                                    '# Grab ip address assined to 1.1',
                                    'INT1ADDRESS=`curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/1/ip\" -H \"Metadata-Flavor: Google\"`',
                                    '# Grab ip address assined to 1.2',
                                    'INT2ADDRESS=`curl -s -f --retry 20 \"http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/2/ip\" -H \"Metadata-Flavor: Google\"`',
                                    '# Determine network from self ip and netmask given',
                                    'prefix2mask() {',
                                    '   local i mask=""',
                                    '   local octets=$(($1/8))',
                                    '   local part_octet=$(($1%8))',
                                    '   for ((i=0;i<4;i+=1)); do',
                                    '       if [ $i -lt $octets ]; then',
                                    '           mask+=255',
                                    '       elif [ $i -eq $octets ]; then',
                                    '           mask+=$((256 - 2**(8-$part_octet)))',
                                    '       else',
                                    '           mask+=0',
                                    '       fi',
                                    '       test $i -lt 3 && mask+=.',
                                    '   done',
                                    '   echo $mask',
                                    '}',
                                    DOTMASK,
                                    DOTMASK2,
                                    'IFS=. read -r i1 i2 i3 i4 <<< ${INT1ADDRESS}',
                                    'IFS=. read -r m1 m2 m3 m4 <<< ${dotmask}',
                                    'network=`printf "%d.%d.%d.%d" "$((i1 & m1))" "$((i2 & m2))" "$((i3 & m3))" "$((i4 & m4))"`',
                                    'GATEWAY=$(echo "`echo $network |cut -d"." -f1-3`.$((`echo $network |cut -d"." -f4` + 1))")',
                                    'IFS=. read -r i1 i2 i3 i4 <<< ${INT2ADDRESS}',
                                    'IFS=. read -r m1 m2 m3 m4 <<< ${dotmask2}',
                                    'network2=`printf "%d.%d.%d.%d" "$((i1 & m1))" "$((i2 & m2))" "$((i3 & m3))" "$((i4 & m4))"`',
                                    'GATEWAY2=$(echo "`echo $network2 |cut -d"." -f1-3`.$((`echo $network2 |cut -d"." -f4` + 1))")',
                                    'PROGNAME=$(basename $0)',
                                    'function error_exit {',
                                    'echo \"${PROGNAME}: ${1:-\\\"Unknown Error\\\"}\" 1>&2',
                                    'exit 1',
                                    '}',
                                    'date',
                                    'declare -a tmsh=()',
                                    'echo \'starting custom-config.sh\'',
                                    USESD,
                                    'if [ -n "${useServiceDiscovery}" ];then',
                                    '   tmsh+=('
                                    '   \'tmsh load sys application template /config/cloud/f5.service_discovery.tmpl\'',
                                    SDAPP,
                                    'else',
                                    '   tmsh+=(',
                                    '   \'tmsh load sys application template /config/cloud/f5.service_discovery.tmpl\')',
                                    'fi',
                                    'tmsh+=(',
                                    '\"tmsh create net vlan external interfaces add { 1.1 } mtu 1460\"',
                                    '\"tmsh create net self ${INT1ADDRESS}/32 vlan external\"',
                                    '\"tmsh create net route ext_gw_int network ${GATEWAY}/32 interface external\"',
                                    EXTRT,
                                    '\"tmsh create net route default gw ${GATEWAY}\"',
                                    '\"tmsh create net vlan internal interfaces add { 1.2 } mtu 1460\"',
                                    '\"tmsh create net self ${INT2ADDRESS}/32 vlan internal allow-service add { tcp:4353 udp:1026 }\"',
                                    '\"tmsh create net route int_gw_int network ${GATEWAY2}/32 interface internal\"',
                                    '\"tmsh modify cm device ${HOSTNAME} unicast-address { { effective-ip ${INT2ADDRESS} effective-port 1026 ip ${INT2ADDRESS} } }\"',
                                    '\"tmsh modify sys db failover.selinuxallowscripts value enable\"',
                                    INTRT,
                                    '\'tmsh save /sys config\'',
                                    '\'bigstart restart restnoded\')',
                                    'for CMD in "${tmsh[@]}"',
                                    'do',
                                    '    if $CMD;then',
                                    '        echo \"command $CMD successfully executed."',
                                    '    else',
                                    '        error_exit "$LINENO: An error has occurred while executing $CMD. Aborting!"',
                                    '    fi',
                                    'done',
                                    'date',
                                    '### START CUSTOM CONFIGURATION',
                                    '### END CUSTOM CONFIGURATION',
                                    'EOF',
                                    'cat <<\'EOF\' > /config/cloud/gce/rm-password.sh',
                                    '#!/bin/bash',
                                    'date',
                                    'echo \'starting rm-password.sh\'',
                                    'rm /config/cloud/gce/.adminPassword',
                                    'date',
                                    'EOF',
                                    'cat <<\'EOF\' > /config/cloud/gce/create-va.sh',
                                    '#!/bin/bash',
                                    'date',
                                    'echo "starting create-va.sh"',
                                    'aliasIpsList=$(echo \'' + context.properties['aliasIp'] + '\' | tr ";" " ")',
                                    'for ip in $aliasIpsList; do',
                                    '   addr=$(echo $ip | cut -d "/" -f1)',
                                    '   echo "creating virtual address: $addr"',
                                    '   /usr/bin/tmsh create ltm virtual-address $addr address $addr',
                                    'done',
                                    '/usr/bin/tmsh save sys config',
                                    '# run failover to ensure objects are on the correct BIG-IP',
                                    '/config/failover/tgactive',
                                    'date',
                                    'EOF',
                                    'curl -s -f --retry 20 -o /config/cloud/f5-cloud-libs.tar.gz https://cdn.f5.com/product/cloudsolutions/f5-cloud-libs/v4.5.0/f5-cloud-libs.tar.gz',
                                    'curl -s -f --retry 20 -o /config/cloud/f5-cloud-libs-gce.tar.gz https://cdn.f5.com/product/cloudsolutions/f5-cloud-libs-gce/v2.3.0/f5-cloud-libs-gce.tar.gz',
                                    'curl -s -f --retry 20 -o /config/cloud/f5.service_discovery.tmpl https://cdn.f5.com/product/cloudsolutions/iapps/common/f5-service-discovery/v2.2.0/f5.service_discovery.tmpl',
                                    'chmod 755 /config/verifyHash',
                                    'chmod 755 /config/installCloudLibs.sh',
                                    'chmod 755 /config/waitThenRun.sh',
                                    'chmod 755 /config/cloud/gce/custom-config.sh',
                                    'chmod 755 /config/cloud/gce/rm-password.sh',
                                    'chmod 755 /config/cloud/gce/create-va.sh',
                                    'mkdir -p /var/log/cloud/google',
                                    'nohup /usr/bin/setdb provision.1nicautoconfig disable &>> /var/log/cloud/google/install.log < /dev/null &',
                                    'nohup /config/installCloudLibs.sh &>> /var/log/cloud/google/install.log < /dev/null &',
                                    'nohup /config/waitThenRun.sh f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/runScript.js --signal PASSWORD_CREATED --file f5-rest-node --cl-args \'/config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/generatePassword --file /config/cloud/gce/.adminPassword --encrypt\' --log-level verbose -o /var/log/cloud/google/generatePassword.log &>> /var/log/cloud/google/install.log < /dev/null &',
                                    'nohup /config/waitThenRun.sh f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/runScript.js --wait-for PASSWORD_CREATED --signal ADMIN_CREATED --file /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/createUser.sh --cl-args \'--user admin --password-file /config/cloud/gce/.adminPassword --password-encrypted\' --log-level debug -o /var/log/cloud/google/createUser.log &>> /var/log/cloud/google/install.log < /dev/null &',
                                    CUSTHASH,
                                    ONBOARDJS,
                                    'CONFIG_FILE=\'/config/cloud/.deployment\'',
                                    'CLOUD_LIBS_DIR=\'/config/cloud/gce/node_modules/@f5devcentral\'',
                                    'echo \'{"tagKey":"f5_deployment","tagValue":"' + context.env['deployment'] + '"}\' > $CONFIG_FILE',
                                    'echo "/usr/bin/f5-rest-node ${CLOUD_LIBS_DIR}/f5-cloud-libs-gce/scripts/failover.js" >> /config/failover/tgactive',
                                    'echo "/usr/bin/f5-rest-node ${CLOUD_LIBS_DIR}/f5-cloud-libs-gce/scripts/failover.js" >> /config/failover/tgrefresh',
                                    'nohup /config/waitThenRun.sh f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/runScript.js --file /config/cloud/gce/custom-config.sh --cwd /config/cloud/gce -o /var/log/cloud/google/custom-config.log --log-level debug --wait-for ONBOARD_DONE --signal CUSTOM_CONFIG_DONE &>> /var/log/cloud/google/install.log < /dev/null &',
                                    CLUSTERJS,
                                    'nohup /config/waitThenRun.sh f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/runScript.js --file /config/cloud/gce/rm-password.sh --cwd /config/cloud/gce -o /var/log/cloud/google/rm-password.log --log-level debug --wait-for CLUSTER_DONE --signal PASSWORD_REMOVED &>> /var/log/cloud/google/install.log < /dev/null &',
                                    'nohup /config/waitThenRun.sh f5-rest-node /config/cloud/gce/node_modules/@f5devcentral/f5-cloud-libs/scripts/runScript.js --file /config/cloud/gce/create-va.sh --cwd /config/cloud/gce --log-level debug --wait-for CLUSTER_DONE --signal VIRTUAL_ADDRESSES_CREATED &>> /var/log/cloud/google/install.log < /dev/null &',
                                    'touch /config/startupFinished',
                                    ])
                            )
            }]
        }
  return metadata
def Instance(context, group, storageName, licenseType):
  aliasIps = []
  if group == 'create':
    aliasIps = [{'ipCidrRange': ip} for ip in context.properties['aliasIp'].split(';')]
  instance = {
        'zone': context.properties['availabilityZone1'],
        'canIpForward': True,
        'tags': {
          'items': ['intfw-' + context.env['deployment'],'no-ip']
        },
        'labels': {
          'f5_deployment': context.env['deployment']
        },
        'machineType': ''.join([COMPUTE_URL_BASE, 'projects/',
                         context.env['project'], '/zones/', context.properties['availabilityZone1'], '/machineTypes/',
                         context.properties['instanceType']]),
        'serviceAccounts': [{
            'email': context.properties['serviceAccount'],
            'scopes': ['https://www.googleapis.com/auth/compute','https://www.googleapis.com/auth/devstorage.read_write']
        }],
        'disks': [{
            'deviceName': 'boot',
            'type': 'PERSISTENT',
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceImage': ''.join([COMPUTE_URL_BASE, 'projects/f5-7626-networks-public',
                                    '/global/images/',
                                    context.properties['imageName'],
                                ])
            }
        }],
        'networkInterfaces': [{
            'network': ''.join([COMPUTE_URL_BASE, 'projects/',
                            context.env['project'], '/global/networks/',
                            context.properties['mgmtNetwork']]),
            'subnetwork': ''.join([COMPUTE_URL_BASE, 'projects/',
                            context.env['project'], '/regions/',
                            context.properties['region'], '/subnetworks/',
                            context.properties['mgmtSubnet']]),
          },
          {
            'network': ''.join([COMPUTE_URL_BASE, 'projects/',
                            context.env['project'], '/global/networks/',
                            context.properties['network1']]),
            'subnetwork': ''.join([COMPUTE_URL_BASE, 'projects/',
                            context.env['project'], '/regions/',
                            context.properties['region'], '/subnetworks/',
                            context.properties['subnet1']]),
            'aliasIpRanges': aliasIps,
          },
          {
              'network': ''.join([COMPUTE_URL_BASE, 'projects/',
                                  context.env['project'], '/global/networks/',
                                  context.properties['network2']]),
              'subnetwork': ''.join([COMPUTE_URL_BASE, 'projects/',
                                  context.env['project'], '/regions/',
                                  context.properties['region'], '/subnetworks/',
                                  context.properties['subnet2']]),
          }],
          'metadata': Metadata(context, group, storageName, licenseType)
    }
  return instance
def GenerateConfig(context):
  import random
  storageNumber = str(random.randint(10000, 99999))
  storageName = 'f5-bigip-' + context.env['deployment'] + '-' + storageNumber
  resources = [{
    'name': 'bigip1-' + context.env['deployment'],
    'type': 'compute.v1.instance',
    'properties': Instance(context, 'create', storageName, 'payg')
  },{
    'name': 'bigip2-' + context.env['deployment'],
    'type': 'compute.v1.instance',
    'properties': Instance(context, 'join', storageName, 'payg')
  },{
    'name': storageName,
    'type': 'storage.v1.bucket',
    'properties': {
      'project': context.env['project'],
      'name': storageName,
    },
  },{
    'name': 'intfirewall-' + context.env['deployment'],
    'type': 'compute.v1.firewall',
    'properties': {
        'network': ''.join([COMPUTE_URL_BASE, 'projects/',
                            context.env['project'], '/global/networks/',
                            context.properties['network2']]),
        'targetTags': ['intfw-'+ context.env['deployment']],
        'sourceTags': ['intfw-'+ context.env['deployment']],
        'allowed': [{
            'IPProtocol': 'TCP',
            'ports': [4353]
            },{
            'IPProtocol': 'UDP',
            'ports': [1026],
        }]
    }
  }]
  return {'resources': resources}