#!/usr/bin/python3
# coding=utf-8
import platform,os,subprocess,json,time,shutil,random,warnings
from optparse import  OptionParser
import pandas as pd
from concurrent.futures import ThreadPoolExecutor,as_completed

'''
shell 静态检查工具shellcheck
'''
TOOLS_PATH='tool'
LOG_PATH = 'logs'
OS_NAME = platform.system().upper()
SHELLCHECK={
    'WINDOWS':'shellcheck-stable.exe',
    'LINUX' : 'shellcheck'
}
PR_DETAILS_URL='https://www.shellcheck.net/wiki/SC'
PY_DIR,FILENAME = os.path.split(os.path.abspath(__file__))
# 创建线程池  指定最大容纳数量为4
EXECUSTOR = ThreadPoolExecutor(max_workers=4)
#忽略
warnings.filterwarnings("ignore")

def get_folder_all_check_file(src_root, support_suffix):
    '''
    扫描目录，获取所有检查文件 list
    :param src_root: 扫描目录
    :param support_suffix: 支持文件后缀
    :return: list_files
    '''
    print('doing get check file')
    if not os.path.exists(src_root):
        print("[ERROR] no exist file:"
              "\n %s" % src_root)
        exit(-1)
    src_root = os.path.abspath(src_root)
    if os.path.isfile(src_root):
        return [src_root]
    list_files = []
    for rt, dirs, files in os.walk(src_root):
        for single_file in files:
            try:
                suffix = single_file.rsplit('.',1)[1]
            except:
                break;
            if suffix in support_suffix:
                list_files.append(os.path.join(rt, single_file))
    return list_files

def  check_file_create_report(list_files, output_report, shellcheck=None, isdel=True):
     '''
     检查文件并且生产报告
     :param list_files:检查文件列表
     :param output_report:输出报告路径
     :param isdel:是否删除日志
     :return: None
     '''
     print('doing checking file')
     # 获取当前执行目录
     cur_dir = os.getcwd()
     shellcheck = get_executable_file(shellcheck)
     shellcheck = prefix_exe(shellcheck)
     take_list = [EXECUSTOR.submit(get_check_file_log,file=file,shellcheck=shellcheck) for file in  list_files]
     #等待3秒
     time.sleep(3)
     thread_results = [take.result() for take in as_completed(take_list) if take != None]
     data = json_to_DataFrame(thread_results=thread_results)
     # 清空日志
     if isdel and os.path.exists(LOG_PATH):
         shutil.rmtree(LOG_PATH, ignore_errors=True)
     # 恢复执行目录
     os.chdir(cur_dir);
     if not output_report:
         output_report = 'report' + format_time(format='%Y%m%d%H%M%S') + '.xlsx'
     print('doing create report')
     try:
        handler_DataFrame_output_excel(data, output_report)
     except :
         print('[ERROR] no create data or all files are not checked: %s'
               '\n please see the log')
         exit(-1)
     print("output report : %s" % os.path.abspath(output_report))




def get_executable_file(shellcheck=None):
    '''

    :param shellcheck: 执行文件路径
    :return:
    '''
    if not shellcheck :
        try:
            shellcheck = SHELLCHECK[OS_NAME]
            os.chdir(os.path.join(PY_DIR, TOOLS_PATH))
            if not os.path.exists(LOG_PATH):
                os.mkdir(LOG_PATH)
            return shellcheck
        except KeyError:
            print('[ERROR] no support OS:'
                  '\n %s' % OS_NAME)
            exit(-1)
    if os.path.isfile(shellcheck):
        shll_dir, shellcheck = os.path.split(os.path.abspath(shellcheck))
        os.chdir(shll_dir)
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        return shellcheck
    else:
        print('[ERROR] no exist shellcheck file:'
              '\n %s' % shellcheck)
        exit(-1)


def get_check_file_log(file, shellcheck, shellcheck_para='--format=json'):
    '''
    检查文件并生成日志
    :param file: 检查文件
    :param shellcheck_para: 参数
    :param shellcheck: 执行文件
    :return:
    '''
    print('doing check file : %s' %file)
    backup_path = file
    log_file = os.path.join(LOG_PATH,str(random.random())[2:]+'.log')
    if OS_NAME == 'WINDOWS':
        shell = False
        copy_file = log_file + '.sh'
        try:
            shutil.copy(file,copy_file)
            file = copy_file
        except  IOError :
            print('[ERROR] backup file CMD:'
                  '\n %s' %file)
    cmd_list=[shellcheck, file, shellcheck_para,'>',log_file]
    #print('cmd:',' '.join(cmd_list))
    out = os.popen(' '.join(cmd_list))
    return log_file,out.read(),backup_path


def prefix_exe(shellcheck):
    if OS_NAME == 'LINUX':
        return './' + shellcheck
    return shellcheck


def json_to_DataFrame(thread_results):
    '''
    :param thread_results:[(log,out,file)]
    :return:
    '''
    df = pd.DataFrame()
    for log,out,file in thread_results:
        if os.path.isfile(log):
            try:
                log_df = pd.read_json(log)
                if OS_NAME == 'WINDOWS':
                    log_df['file']=file
                df = df.append(log_df)
            except:
                print('[ERROR] read log file failed: %s' %file)
        else:
            print('[ERROR] check file failed , no create log file :'
                  '\n %s' % file)
    return df

def handler_DataFrame_output_excel(df,file):
    '''
    处理数据 输出报告
    :param df:DataFrame
    :param file:输出报告路径
    :return:
    '''
    columns = ['file','line','level','code','details_url','message']

    #排序
    #df.sort_values(by='level')

    # data根据'file', 'line'组合列删除重复项，默认保留第一个出现的值组合。传入参数keep='last'则保留最后一个
    df = df.drop_duplicates(['file', 'line'])
    # 设置详情连接
    # 使用apply函数,  url 列  = code字段 + CODE_URL
    df['details_url'] = df['code'].apply(lambda x: PR_DETAILS_URL + str(x))
    df.to_excel(file,sheet_name='shellcheck',columns=columns)

def args_handler(arg, isRetList=False,interval=','):
    '''
    suf str handler
    :param arg:
    :param isRetList: 是否return List
    :param interval: 间隔符
    :return:[],string
    '''
    if arg == None :
        return None
    if (arg[0] =='\'' and arg[-1] =='\'') | (arg[0] =='\"' and arg[-1] =='\"'):
        arg = arg[1:-1]
    if not isRetList:
        return arg
    else:
        return arg.split(interval)

def format_time(times=time.time(), format='%Y-%m-%d %H:%M:%S'):
    '''
    格式化日期
    :param times:
    :return:
    '''
    return time.strftime(format, time.localtime(times))

if __name__ == '__main__':
    parser = OptionParser('[*] Usage : ./' +FILENAME +
                          '\n -f <check file or directory>'
                          '\n -s <Specify dialect (sh, bash, dash, ksh), support file suffix, default sh>'
                          '\n -o <output report excel file path ,default current directory excel file>'
                          '\n -e <shellcheck file,default ./tools/shellcheck-stable.exe or ./tools/shellcheck>'
                          )
    parser.add_option('-f','--file', dest='file', type='string', default=None)
    parser.add_option('-s','--suffix', dest='suffix', type='string', default='sh')
    parser.add_option('-o','--output', dest='output', type='string', default=None)
    parser.add_option('-e','--exe', dest='exe', type='string', default=None)
    (options, args) = parser.parse_args()
    # 参数处理
    if (options.file == None):
        print(parser.usage)
        exit(1)

    start_time = time.time();
    print("===start===", format_time(start_time))
    options.file = args_handler(options.file)
    options.suffix = args_handler(options.suffix,True)
    options.output = args_handler(options.output)
    options.exe = args_handler(options.exe)
    print("os name : ", OS_NAME)
    list_files=get_folder_all_check_file(src_root=options.file,
                              support_suffix=options.suffix)

    #检查文件并且生产报告
    check_file_create_report(list_files=list_files,
                             output_report=options.output,
                             shellcheck=options.exe)

    end_time = time.time()
    print("===end===", format_time(end_time))
    print("===finish=== Total execution time:", '%.2f' % (end_time - start_time), "秒")
    exit(0)

