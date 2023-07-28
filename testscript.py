from __future__ import print_function
import os
import subprocess
import sys
import time

script_path = os.path.dirname(os.path.realpath(__file__))
minio_keypair = '/var/lib/irods/minio.keypair'
bucket_name = '/threadbucket'
endpoint_domain = '127.0.0.1:9000'
log_level = 'INFO'
event_handler = 'irods_capability_automated_ingest/examples/put.py'
log_path = '/var/lib/irods/log/performance/'
coll_path = '/tempZone/home/rods/'
trash_path = '/var/lib/irods/Vault/trash/home/'
file_dir_name = 'testfiles'

def run_cmd(cmd, run_env=False, unsafe_shell=False, check_rc=False):
    # run it
    if run_env == False:
        run_env = os.environ.copy()
    if unsafe_shell == True:
        p = subprocess.Popen(cmd, env=run_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    else:
        p = subprocess.Popen(cmd, env=run_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    # if cmd[0]=="du" or cmd[0]=="sudo":
    #     print(out.decode())
    if check_rc != False:
        if p.returncode != 0:
            sys.exit(p.returncode)
    return p.returncode

def del_delay(device):
    run_cmd(['sudo', 'tc', 'qdisc', 'del', 'dev', device, 'root', 'netem'], check_rc=True)
def add_delay(device, total_milliseconds):
    run_cmd(['sudo', 'tc', 'qdisc', 'add', 'dev', device, 'root', 'netem', 'delay', '{0}ms'.format(total_milliseconds)], check_rc=True)


def get_ingest_job(log_name, coll_name, threads, files_per_task):

    do_parallel = 0 if int(threads)==1 else 1
    cmd = ['python', '-m', 'irods_capability_automated_ingest.irods_sync', 'start',
           '--ignore_cache',
           '--event_handler', event_handler,
           '--synchronous',
           '--progress',
           '--s3_keypair', minio_keypair,
           '--s3_endpoint_domain', endpoint_domain,
           '--s3_insecure_connection',
           '--rec_threads', threads,
           '--do_parallel', str(do_parallel),
           '--log_filename', log_path+log_name+'.log',
           '--log_level', log_level,
           '--files_per_task', files_per_task,
           bucket_name,
           coll_path+coll_name]
    return cmd

def copy_to_bucket():
    return ['mc', 'cp', '-r', 'testfiles/', 'mymin/threadbucket/']

def clear_bucket():
    return ['mc', 'rm', '-r', '--force', 'mymin/threadbucket/']

def main():
    filesize_array    = ['1', '5', '10', '100', '500'] #['1000', '5000']
    num_files         = [1, 15]
    delay_array       = ['0', '50', '100']
    num_threads_array =  ['1', '2', '3', '4', '8']
    files_per_task_array = ['1', '3']
    runs_of_each      = 5



    results_file = "results.csv"
    # csv headers
    with open(os.path.join(script_path, results_file), 'a') as f:
        f.write('MiB,numfiles,delay,N,fpt,run,seconds\n')

    for filesize in filesize_array:
        for num in num_files:
            for delay in delay_array:
                # set_delay('eth0', delay)
                for num_threads in num_threads_array:
                    for files_per_task in files_per_task_array:
                        for run in range(1, runs_of_each+1):
                            run_cmd(['mkdir', file_dir_name])
                            for filenum in range(num):
                                filename = f'testfiles/sparsefile{filenum}'
                                run_cmd(['touch', filename])
                                run_cmd(['truncate', '-s', f'+{filesize}M', filename])
                            run_cmd(copy_to_bucket())
                            name = filesize+'M'+str(num)+'N'+delay+'D'+num_threads+'T'+files_per_task+'F'+str(run)+'R'
                            ingest_cmd = get_ingest_job(name, name, num_threads, files_per_task)
                            run_cmd(['imkdir', name], check_rc=True)
                            add_delay('eth0', delay)
                            start = time.time()
                            run_cmd(ingest_cmd, check_rc=True)
                            end = time.time()
                            del_delay('eth0')
                            duration = end - start
                            with open(os.path.join(script_path, results_file), 'a') as f:
                                line = [filesize, str(num), delay, num_threads, files_per_task, str(run), str(duration)]
                                f.write(','.join(line))
                                f.write('\n')
                            
                            run_cmd(['du', '--apparent-size','-b', file_dir_name])
                            run_cmd(['rm', '-rf', file_dir_name])
                            run_cmd(clear_bucket())
                            run_cmd(['du', '--apparent-size','-b', '/var/lib/irods/Vault/home/rods/'+name])
                            run_cmd(['irm', '-r', name])
                            run_cmd(['rm', '-rf', trash_path])



    run_cmd(['sudo', 'tc', 'qdisc', 'del', 'dev', 'eth0', 'root', 'netem'], check_rc=True)



if __name__ == '__main__':
    #main()
    sys.exit(main())
                          
