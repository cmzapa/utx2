import subprocess
import requests
import socket
import netifaces as ni
import platform
import time
import schedule

token = None
ip = "10.10.10.1" # Set initial IP. This approach may need to be re-examined #TODO
rest_ip = "10.92.1.33" # Set initial REST IP for server #TODO
# rest_ip = "10.139.57.107" # This is an old IP, and should likely be removed #TODO
status = None
heartbeat_frequency = 20 # Set default heartbeat_frequency #TODO


# checks to see if the Jupyter container is running
def is_running():
    """ Function: is_running()
    Using subprocess library calls to docker to check if the TX2 container is running
    Returns: string
    """

    global status
    p = subprocess.getoutput("docker inspect -f '{{.State.Running}}' TX2-UofA-CUDA-GPU-Jupyter")

    if p == 'true':
        status = "On"
        return True
    else:
        status = "Off"
        return False


# get the jupyter notbook token
def get_token():
    """ Function: get_token()
    The subprocess library calls TX2 container to obtain jupyter notebook URL as token
    Returns: string
    """

    print("jupyter container is running: ", is_running())
    
    if is_running():
        global token
        token = None

        # p = subprocess.getoutput('docker logs TX2-UofA-CUDA-GPU-Jupyter 2>&1 | grep token') #TODO
        # p = subprocess.getoutput('docker exec -i TX2-UofA-CUDA-GPU-Jupyter jupyter notebook list') #TODO
        command = '''
        docker exec -i TX2-UofA-CUDA-GPU-Jupyter jupyter notebook list|awk -F= '{ print $2 }'|awk '{ print $1 }' |tail -1
        '''
        p = subprocess.getoutput(command)
        print("Process output: {}".format(str(p)))
        token = ''.join(p)
        
        print("Token: ", token)

        if token == "the input device is not a TTY":
            time.sleep(5)
            print("waiting 5 seconds to see if the docker container is up yet")
            get_token()

        #start = 'token=' #TODO
        #end = ' ::' #TODO
        #token = ((raw_token.split(start))[1].split(end)[0]) #TODO

        print("Token: ", token)
    else:
        token = "None"


# post Jettson data to rest interface
def post_data():
    """ Function: post_data()
    Submits ip, jupyterToken, startedAt and and Status of TX2 container to server listening at rest_ip:8888/submit
    Returns: string
    """

    try:
        global status
        global rest_ip

        api_endpoint = "http://" + rest_ip + ":8008/submit"
        data = {
            "ip": ip,
            "jupyterToken": token,
            "status": status,
            "startedAt": "2020-05-08T02:51:15.52592226Z"
            }
        print("trying to post data to rest endpoint: {}".format(data), api_endpoint)

        r = requests.post(url=api_endpoint, json=data, timeout=10)

        # extracting response text
        print("response: ", r.text)

        return "done"
    except requests.exceptions.RequestException as e:
        print("Unable to post data", e)


# Function to display hostname and
# IP address
def get_host_name_ip():
    """ Function: get_host_name()
    Uses socket library to obtain hostname
    Returns: string
    """
    try:
        global ip
        host_ip = ""
        host_name = socket.gethostname()
        os = platform.system()
        if os == "Windows":
            host_ip = socket.gethostbyname(host_name)


        else:
            host_ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']

        ip = host_ip
        print("TX2 IP: ", ip)
    except:
        print("Unable to get Hostname and IP")

    # Driver code


# calls the rest server to see if it needs to change the API endpoint
def update_rest_ip():
    """ Function: update_rest_ip()
    Hits rest_ip:8888/endpoint obtain updated IP for REST_API (rest_ip) and heartbeat_frequency
    Returns: string
    """
    print("update rest IP")
    global rest_ip
    global heartbeat_frequency
    # api_url = "http://" + rest_ip + ":8008/endpoint" #this variable is not used
    try:
        r = requests.get("http://" + rest_ip + ":8008/endpoint", timeout=10)
        print("response from update rest IP: ", r.json())
        data = r.json()
        print("data.ip: ", data['ip'])
        rest_ip = data['ip']
        heartbeat_frequency = data['heartbeatFreq']
        print("new REST_API IP: ", rest_ip)
        print("new freq: ", heartbeat_frequency)
    except:
        print("couldn't get an update for the IP or heartbeat frequency")


#     post to rest endpoint on a regular basis
def heart_beat():
    """ Function: heart_beat()
    This function calls get_token, get_host_name_ip, post_data, and update_rest_ip in order
    Returns: none
    """
    get_token()
    get_host_name_ip()
    post_data()
    update_rest_ip()


get_token()
get_host_name_ip()
post_data()
schedule.every(20).seconds.do(heart_beat)
while True:
    schedule.run_pending()
    time.sleep(1)
