def gen_routinator_conf():
    """
    Generates the configuration content for Routinator.

    :return: A list of strings representing the Routinator configuration.
    """
    lista_stringhe_routinator = []
    lista_stringhe_routinator.extend([
        "allow-dubious-hosts = true",  # Allow connections from hosts with dubious certificates
        "dirty = false",  # Ensure clean validation runs
        #"disable-rrdp = false",
        #"disable-rsync = true",
        "no-rir-tals = true",  # Disable the use of built-in TALs from RIRs
        "exceptions = [\"/root/rpki_exceptions.json\"]",  # Path to the exceptions file
        "expire = 7200",  # Time in seconds before validation data expires
        "history-size = 10",  # Number of validation runs to keep in history
        "http-listen = [\"0.0.0.0:9556\"]",  # HTTP server listening address
        "pid-file = \"/run/routinator.pid\"",  # Path to the PID file
        "log = \"file\"",  # Log output destination
        "log-file = \"/var/log/routinator.log\"",  # Path to the log file
        "log-level = \"WARN\"",  # Minimum log level
        "refresh = 10",  # Refresh interval in seconds
        "repository-dir = \"/root/.rpki-cache/repository\"",  # Directory for RPKI repository
        "retry = 30",  # Retry interval in seconds
        "rrdp-proxies = []",  # List of RRDP proxy servers
        "rrdp-root-certs = []",  # List of additional RRDP root certificates
        "rsync-command = \"rsync\"",  # Command used for rsync operations
        "rsync-timeout = 300",  # Timeout for rsync in seconds
        "rtr-listen = [\"0.0.0.0:3323\"]",  # RTR server listening address
        "rtr-tcp-keepalive = 60",  # TCP keepalive interval in seconds
        "stale = \"reject\"",  # Action to take for stale data
        "strict = false",  # Enable strict validation
        "syslog-facility = \"daemon\"",  # Syslog facility
        "systemd-listen = false",  # Disable systemd socket activation
        "extra-tals-dir = \"/root/.rpki-cache/tals\"",  # Directory for additional TALs
        "unknown-objects = \"warn\"",  # Log unknown objects as warnings
        "unsafe-vrps = \"warn\"",  # Log unsafe VRPs as warnings
        "validation-threads = 1"  # Number of threads for validation
    ])
    return lista_stringhe_routinator

def gen_krill_conf(address_krill):
    """
    Generates the configuration content for Krill.

    :param address_krill: The IP address of the Krill server.
    :return: A list of strings representing the Krill configuration.
    """
    lista_stringhe_krill = []
    lista_stringhe_krill.extend([
        "# General configuration for Krill",
        f"ip = \"{address_krill}\"",  # IP address for the Krill server
        "port = 3001",  # Port for the Krill server
        "data_dir = \"/etc/krill/\"",  # Directory for Krill data
        "pid_file = \"/etc/krill/krill.pid\"",  # Path to the PID file
        "repo_enabled = true",  # Enable the repository
        "log_type = \"stderr\"",  # Log output destination
        "rsync_base = \"rsync://rpki-server.org:3000/repo/\"",  # Base URI for RSYNC
        "service_uri  = \"https://rpki-server.org:3000/\"",  # Service URI
        "auth_token   = \"kathara-secret-token\"",  # Authentication token
        "bgp_risdumps_enabled = false",  # Disable BGP RIS dumps
        "timing_roa_valid_weeks = 2",  # ROA validity period in weeks
        "timing_roa_reissue_weeks_before = 1",  # Reissue ROAs 1 week before expiration
        "[testbed]",  # Testbed-specific configurations
        "rrdp_base_uri = \"https://rpki-server.org:3000/rrdp/\"",  # Base URI for RRDP
        "rsync_jail = \"rsync://rpki-server.org:3000/repo/\"",  # Jail for RSYNC operations
        "ta_aia = \"rsync://rpki-server.org:3000/ta/ta.cer\"",  # Trust Anchor AIA URI
        "ta_uri = \"https://rpki-server.org:3000/ta/ta.cer\""  # Trust Anchor URI
    ])
    return lista_stringhe_krill

def gen_haproxy_cfg(address_krill):
    """
    Generates the configuration content for HAProxy.

    :param address_krill: The IP address of the Krill server.
    :return: A list of strings representing the HAProxy configuration.
    """
    lista_stringhe_haproxy = []
    lista_stringhe_haproxy.extend([
        "global",
        "    log         127.0.0.1 local2",  # Log to local syslog
       #"    chroot      /var/lib/haproxy",
       #"    chroot      /run/haproxy",
       #"    pidfile     /run/haproxy.pid",
        "    maxconn     4000",  # Maximum number of connections
        "defaults",
        "    mode                    tcp",  # Default mode: TCP
        "    log                     global",  # Use global logging
        "    option                  tcplog",  # Enable TCP log format
        "    option                  dontlognull",  # Don't log null connections
        "    option                  redispatch",  # Retry requests if servers are full
        "    retries                 3",  # Number of retries before giving up
        "    timeout http-request    10s",  # Timeout for HTTP requests
        "    timeout queue           1m",  # Timeout for request queue
        "    timeout connect         10s",  # Timeout for connecting to servers
        "    timeout client          1m",  # Timeout for client connections
        "    timeout server          1m",  # Timeout for server responses
        "    timeout http-keep-alive 10s",  # Timeout for HTTP keep-alive
        "    timeout check           10s",  # Timeout for health checks
        "    maxconn                 3000",  # Maximum number of connections per frontend/backend
        "frontend mini_internet",
        "    bind *:3000 ssl crt /etc/ssl/certs/cert.includesprivatekey.pem",  # SSL certificate
        "    mode http",  # HTTP mode
        "    acl testbed_in_uri path_beg /testbed",  # ACL for testbed URI
        "    use_backend krill unless testbed_in_uri",  # Use Krill backend unless ACL matches
        "    default_backend no-match",  # Default backend for no matches
        "frontend mini_internet_insecure",
        "    bind *:80",  # Bind to port 80 for HTTP
        "    mode http",
        "    acl testbed_in_uri path_beg /testbed",
        "    use_backend krill unless testbed_in_uri",
        "    default_backend no-match",
        "backend krill",
        "    mode http",
       f"    server krill_server {address_krill}:3001 ssl check check-ssl verify none",  # Krill backend server
        "backend no-match",
        "    mode http",
        "    http-request deny deny_status 403"  # Deny unmatched requests with 403
    ])
    return lista_stringhe_haproxy

def gen_rpki_exception():
    """
    Generates the RPKI exceptions configuration content.

    :return: A list of strings representing the RPKI exceptions JSON structure.
    """
    exception = []
    exception.extend([
        "{",
        "    \"slurmVersion\": 1,",  # SLURM file version
        "    \"validationOutputFilters\": {",
        "        \"prefixFilters\": [],",  # Empty prefix filters
        "        \"bgpsecFilters\": []",  # Empty BGPsec filters
        "    },",
        "    \"locallyAddedAssertions\": {",
        "        \"prefixAssertions\": [],",  # Empty prefix assertions
        "        \"bgpsecAssertions\": []",  # Empty BGPsec assertions
        "    }",
        "}"
    ])
    return exception