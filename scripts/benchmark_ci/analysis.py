import argparse
import ast
import json
import os


def parse_args():
    """
    Parse the args of command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log_path',
        type=str,
        default='../../logs/static',
        help='path of benchmark logs')
    parser.add_argument(
        '--standard_path',
        type=str,
        default='../../scripts/benchmark_ci/standard_value/static',
        help='path of standard_value')
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.05,
        help='threshold')
    parser.add_argument(
        '--loss_threshold',
        type=float,
        default=0.3,
        help='loss threshold')
    parser.add_argument(
        '--paddle_dev',
        type=ast.literal_eval,
        default=False,
        help='whether the standard value is generated by paddle develop')
    args = parser.parse_args()
    return args


def traverse_logs(log_path):
    file_list = []
    for dirpath, dirnames, filenames in os.walk(log_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_list.append(file_path)

    print('file_list:{}'.format(file_list))
    return file_list


def analysis(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        try:
            job_info = json.loads(lines[-1])
        except Exception as e:
            print("file {} analysis error.".format(file))
        model = json.dumps(job_info["model_name"])
        model = model.strip('"')
        fail_flag = json.dumps(job_info["JOB_FAIL_FLAG"])
        result = json.dumps(job_info["FINAL_RESULT"])
        loss_result = json.dumps(job_info["LOSS_RESULT"])
        loss_result = loss_result.strip('"')
        loss_result = loss_result.strip(',')
    return model, fail_flag, result, loss_result


def compare():
    file_list = traverse_logs(args.log_path)
    errorcode = 0
    has_file = os.path.exists('errorcode.txt')
    if has_file:
        with open('errorcode.txt', 'r') as f:
            for line in f:
                errorcode = int(line.strip('\n'))
                print('errorcode:{}'.format(errorcode))
    for file in file_list:
        model, fail_flag, result, loss_result = analysis(file)
        if int(fail_flag) == 1:
            command = 'sed -i "s/success/fail/g" log.txt'
            errorcode = errorcode | 4
            os.system(command)
            print("{} running failed!".format(model))
        else:
            print("result:{}".format(result))
            print("result_loss:{}".format(loss_result))
            print("model:{}".format(model))
            standard_record = os.path.join(args.standard_path, model + '.txt')
            loss_standard_record =  os.path.join(args.standard_path, model + '_loss' + '.txt')
            with open(standard_record, 'r') as f:
                for line in f:
                    standard_result = float(line.strip('\n'))
                    print("standard_result:{}".format(standard_result))
                    ranges = round((float(result) - standard_result) / standard_result, 4)
                    if ranges >= args.threshold:
                        if args.paddle_dev:
                            command = 'sed -i "s/success/fail/g" log.txt'
                            errorcode = errorcode | 2
                            os.system(command)
                            print("{}, FAIL".format(model))
                            print(
                                "Performance of model {} has been increased from {} to {},"
                                "which is greater than threshold, "
                                "please contact xiege01 or heya02 to modify the standard value"
                                .format(model, standard_result, result))
                        else:
                            print("Performance of model {} has been increased from {} to {},"
                                  "rerun in paddle develop".format(model, standard_result, result))
                            f = open('rerun_model.txt', 'a')
                            f.writelines(model+'\n')             
                    elif ranges <= -args.threshold:
                        if args.paddle_dev:
                            command = 'sed -i "s/success/fail/g" log.txt'
                            errorcode = errorcode | 2
                            os.system(command)
                            print("{}, FAIL".format(model))
                            print("Performance of model {} has been decreased from {} to {},"
                                  "which is greater than threshold."
                                  .format(model, standard_result, result))
                        else:
                            print("Performance of model {} has been decreased from {} to {},"
                                  "rerun in paddle develop".format(model, standard_result, result))
                            f = open('rerun_model.txt', 'a')
                            f.writelines(model+'\n')
                    else:
                        print("{}, Performance_test, SUCCESS".format(model))
            with open(loss_standard_record, 'r') as f:
                for line in f:
                    loss_standard_result = float(line.strip('\n'))
                    loss_ranges = round((float(loss_result) - loss_standard_result) / loss_standard_result, 4)
                    print("loss result:{}".format(loss_result))
                    print("loss standard result:{}".format(loss_standard_result))
                    if loss_ranges >= args.loss_threshold:
                        if args.paddle_dev:
                            pass
                        else:
                            command = 'sed -i "s/success/fail/g" log.txt'
                            errorcode = errorcode | 1
                            os.system(command)
                            print("{}, FAIL".format(model))
                            print("Final loss of model {} has been increased from {} to {},"
                                  " which is greater than threashold"
                                  .format(model, loss_standard_result, loss_result))
                    else:
                        print("{}, Precision_test, SUCCESS".format(model))
                        
    f = open('errorcode.txt', 'w')
    f.writelines(str(errorcode))
    f.close()

if __name__ == '__main__':
    args = parse_args()
    compare()