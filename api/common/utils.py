#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import traceback
import numpy as np
import json
import collections
import subprocess
import special_op_list


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Unsupported value encountered.')


def run_command(command, shell=True):
    print("run command: %s" % command)
    p = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)

    exit_code = None
    stdout = ''
    while exit_code is None or line:
        exit_code = p.poll()
        line = p.stdout.readline().decode('utf-8')
        stdout += line

    return stdout, exit_code


def compare(output1, output2, atol):
    if not isinstance(output1, np.ndarray) or not isinstance(output2,
                                                             np.ndarray):
        raise TypeError("input argument's type should be numpy.ndarray.")

    max_diff = np.float32(-0.0)
    offset = -1
    try:
        assert len(output1) == len(output2)
        if output1.dtype == np.bool:
            diff = np.array_equal(output1, output2)
            max_diff = np.float32(np.logical_not(diff))
            if diff == False:
                for i in range(len(output1)):
                    if output1[i] != output2[i]:
                        offset = i
            assert np.array_equal(output1, output2)
        else:
            diff = np.abs(output1 - output2)
            max_diff = np.max(diff)
            offset = np.argmax(diff)
            assert np.allclose(output1, output2, atol=atol)
    except (AssertionError) as e:
        pass
    return max_diff, offset


def check_outputs(list1, list2, name, atol=1e-6):
    if not isinstance(list1, list) or not isinstance(list2, list):
        raise TypeError(
            "input argument's type should be list of numpy.ndarray.")

    consistent = True
    max_diff = np.float32(0.0)

    assert len(list1) == len(list2)
    num_outputs = len(list1)
    for i in xrange(num_outputs):
        output1 = list1[i]
        output2 = list2[i]

        max_diff_i, offset_i = compare(output1, output2, atol)
        if max_diff_i > atol:
            print("---- The %d-th output (shape: %s, data type: %s) has diff. "
                  "The maximum diff is %e, offset is %d: %s vs %s." %
                  (i, str(output1.shape), str(output1.dtype), max_diff_i,
                   offset_i, str(output1.flatten()[offset_i]),
                   str(output2.flatten()[offset_i])))

        max_diff = max_diff_i if max_diff_i > max_diff else max_diff
        if max_diff > atol:
            consistent = False

    status = collections.OrderedDict()
    status["name"] = name
    status["consistent"] = consistent
    status["num_outputs"] = num_outputs
    status["diff"] = max_diff.astype("float")

    if not consistent:
        if name is not None and name in special_op_list.RANDOM_OP_LIST:
            print(
                "---- The output is not consistent, but %s is in the white list."
                % name)
            print(json.dumps(status))
        else:
            print(json.dumps(status))
            assert consistent == True, "The output is not consistent."
    else:
        print(json.dumps(status))


def print_benchmark_result(result, log_level=0):
    if not isinstance(result, dict):
        raise TypeError("Input result should be a dict.")

    runtimes = result.get("total", None)
    gpu_time = result.get("gpu_time", None)
    stable = result.get("stable", None)
    diff = result.get("diff", None)

    repeat = len(runtimes)
    for i in range(repeat):
        runtimes[i] *= 1000

    sorted_runtimes = np.sort(runtimes)
    if repeat <= 2:
        num_excepts = 0
    elif repeat <= 10:
        num_excepts = 1
    elif repeat <= 20:
        num_excepts = 5
    else:
        num_excepts = 10
    begin = num_excepts
    end = repeat - num_excepts
    avg_runtime = np.average(sorted_runtimes[begin:end])

    # print all times
    seg_range = [0, 0]
    if log_level == 0:
        seg_range = [0, repeat]
    elif log_level == 1 and repeat > 20:
        seg_range = [10, repeat - 10]
    for i in range(len(runtimes)):
        if i < seg_range[0] or i >= seg_range[1]:
            print("Iter {0}, Runtime: {1}".format("%4d" % i, "%.5f ms" %
                                                  runtimes[i]))

    status = collections.OrderedDict()
    status["framework"] = result["framework"]
    status["version"] = result["version"]
    status["name"] = result["name"]
    status["device"] = result["device"]
    if stable is not None and diff is not None:
        status["precision"] = collections.OrderedDict()
        status["precision"]["stable"] = stable
        status["precision"]["diff"] = diff
    status["speed"] = collections.OrderedDict()
    status["speed"]["repeat"] = len(sorted_runtimes)
    status["speed"]["begin"] = begin
    status["speed"]["end"] = end
    status["speed"]["total"] = avg_runtime
    if gpu_time is not None:
        status["speed"]["gpu_time"] = gpu_time
    print(json.dumps(status))