from asyncio import subprocess
import numpy as np
import time, copy
from federatedml.FATE_Engine.python.BatchPlan.planner.batch_plan import BatchPlan
from federatedml.FATE_Engine.python.BatchPlan.storage.data_store import DataStorage
from federatedml.FATE_Engine.python.BatchPlan.encoding.encoder import BatchEncoder
from federatedml.FATE_Engine.python.BatchPlan.encryption.encrypt import BatchEncryption
from federatedml.FATE_Engine.python.bigintengine.gpu.gpu_store import FPN_store, PEN_store
from federatedml.secureprotol.fate_paillier import PaillierKeypair, PaillierPublicKey, PaillierPrivateKey, PaillierEncryptedNumber

from federatedml.secureprotol import PaillierEncrypt
from federatedml.secureprotol.fixedpoint import FixedPointNumber

import multiprocessing
from threading import Thread

N_JOBS = multiprocessing.cpu_count()
# N_JOBS = 10

class MyThread(Thread):
    def __init__(self, func, args):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        temp = self.func(self.args)
        self.result = temp.sum()

    def get_result(self):
        try:
            return self.result
        except Exception:
            return None

def test_encryption():
    '''Init test vector'''
    row_vec_A = np.random.uniform(-1, 1, 100000)
    row_vec_A = row_vec_A.astype(np.float32)        # use float data type (precision is 23 bits)
    elements_num = row_vec_A.size
    key_generator = PaillierEncrypt()
    key_generator.generate_key()
    '''Init batch encoder'''
    max_value, element_mem_size, encode_slot_mem, encode_sign_bits = 1, 24, 144, 40
    max_element_num = int(1024 / encode_slot_mem)
    split_num = int(np.ceil(len(row_vec_A) / max_element_num))
    encoder = BatchEncoder(max_value, element_mem_size, encode_slot_mem, encode_sign_bits, max_element_num)
    row_vec = np.hstack((row_vec_A, np.zeros(max_element_num * split_num - elements_num)))
    row_vec_used_in_cpu = row_vec.reshape(split_num, max_element_num)
    print("\n--------------------------------------Encoding Test Report:--------------------------------------")
    print("\n-------------------CPU:-------------------")
    start_time = time.time()
    # use multi-process
    # pool = multiprocessing.Pool(processes=N_JOBS)
    # sub_process = [pool.apply_async(FixedPointNumber.encode, (v, key_generator.public_key.n, key_generator.public_key.max_int,)) for v in row_vec_A]
    # pool.close()
    # pool.join()
    # CPU_encode_num_list = [p.get() for p in sub_process]
    # use single process
    CPU_encode_num_list = [FixedPointNumber.encode(v, key_generator.public_key.n, key_generator.public_key.max_int) for v in row_vec_A]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------CPU with BatchEncode:-------------------")
    start_time = time.time()
    # encode
    # use multi-processes
    # pool = multiprocessing.Pool(processes=N_JOBS)
    # sub_process = [pool.apply_async(encoder.batchEncode, (slot_number,)) for slot_number in row_vec_used_in_cpu]
    # pool.close()
    # pool.join()
    # CPU_with_batch_encode_number_list = [p.get() for p in sub_process]
    # use single process
    CPU_with_batch_encode_number_list = [encoder.batchEncode(slot_number) for slot_number in row_vec_used_in_cpu]    # a list of BatchEncodeNumber
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU:-------------------")
    # start_time = time.time()
    # fpn_store = FPN_store.init_from_arr(row_vec_A, key_generator.public_key.n, key_generator.public_key.max_int)
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU with BatchEncode:-------------------")
    # start_time = time.time()
    # fpn_store_with_batch = FPN_store.batch_encode(row_vec, encoder.scaling, encoder.size, encoder.slot_mem_size, encoder.bit_width, encoder.sign_bits, key_generator.public_key)
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))

    print("\n--------------------------------------Encryption Test Report:--------------------------------------")
    print("\n-------------------CPU:-------------------")
    start_time = time.time()
    # use multi-processes
    pool = multiprocessing.Pool(processes=N_JOBS)
    sub_process = [pool.apply_async(key_generator.public_key.raw_encrypt, (v.encoding,)) for v in CPU_encode_num_list]
    pool.close()
    pool.join()
    pen_list = [PaillierEncryptedNumber(key_generator.public_key, p.get(), v.exponent) for p, v in zip(sub_process, CPU_encode_num_list)]
    # use single process
    # pen_list = [PaillierEncryptedNumber(key_generator.public_key, key_generator.public_key.raw_encrypt(v.encoding), v.exponent) for v in CPU_encode_num_list]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------CPU with BatchEncode:-------------------")
    start_time = time.time()
    # multi-processes
    pool = multiprocessing.Pool(processes=N_JOBS)
    sub_process = [pool.apply_async(key_generator.public_key.raw_encrypt, (v,)) for v in CPU_with_batch_encode_number_list]
    pool.close()
    pool.join()
    pen_with_batch_list = [PaillierEncryptedNumber(key_generator.public_key, p.get(), 0) for p in sub_process]
    # single process
    # pen_with_batch_list = [PaillierEncryptedNumber(key_generator.public_key, key_generator.public_key.raw_encrypt(v), 0) for v in CPU_with_batch_encode_number_list]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU:-------------------")
    # start_time = time.time()
    # pen_store = fpn_store.encrypt(key_generator.public_key)
    # pen_store = pen_store.obfuscation()
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU with BatchEncode:-------------------")
    # encrypter = BatchEncryption()
    # start_time = time.time()
    # pen_with_batch_store = encrypter.gpuBatchEncrypt(fpn_store_with_batch, encoder.scaling, encoder.size, key_generator.public_key)
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))

    print("\n--------------------------------------Decryption Test Report:--------------------------------------")
    print("\n-------------------CPU:-------------------")
    start_time = time.time()
    pool = multiprocessing.Pool(processes=N_JOBS)
    sub_process = [pool.apply_async(key_generator.privacy_key.decrypt, (v,)) for v in pen_list]
    pool.close()
    pool.join()
    CPU_decrypt_number_list = [p.get() for p in sub_process]
    # single process
    # CPU_decrypt_number_list = [key_generator.privacy_key.decrypt(v) for v in pen_list]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------CPU with BatchEncode:-------------------")
    start_time = time.time()
    pool = multiprocessing.Pool(processes=N_JOBS)
    sub_process = [pool.apply_async(key_generator.privacy_key.decrypt, (v,)) for v in pen_with_batch_list]
    pool.close()
    pool.join()
    CPU_with_batch_decrypt_number_list = [p.get() for p in sub_process]
    # single process
    # CPU_with_batch_decrypt_number_list = [key_generator.privacy_key.decrypt(v) for v in pen_with_batch_list]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU:-------------------")
    # start_time = time.time()
    # GPU_decrypt_number_list = pen_store.decrypt_without_decode(key_generator.privacy_key)
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU with BatchEncode:-------------------")
    # start_time = time.time()
    # GPU_with_batch_decrypt_number_list = encrypter.gpuBatchDecrypt(pen_with_batch_store, key_generator.privacy_key)
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))

    print("\n--------------------------------------Decode Test Report:--------------------------------------")
    print("\n-------------------CPU:-------------------")
    start_time = time.time()
    # multi-processes
    pool = multiprocessing.Pool(processes=N_JOBS)
    sub_process = [pool.apply_async(v.decode, ()) for v in CPU_decrypt_number_list]
    pool.close()
    pool.join()
    CPU_decode_number_list = [p.get() for p in sub_process]
    # single process
    # CPU_decode_number_list = [v.decode() for v in CPU_decrypt_number_list]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------CPU with BatchEncode:-------------------")
    start_time = time.time()
    # multi-processes
    pool = multiprocessing.Pool(processes=N_JOBS)
    sub_process = [pool.apply_async(encoder.batchDecode, (v.encoding, encoder.scaling, encoder.size,)) for v in CPU_with_batch_decrypt_number_list]
    pool.close()
    pool.join()
    CPU_with_batch_decode_number_list = [p.get() for p in sub_process]
    # single process
    # CPU_with_batch_decode_number_list = [encoder.batchDecode(v.encoding, encoder.scaling, encoder.size) for v in CPU_with_batch_decrypt_number_list]
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU:-------------------")
    # start_time = time.time()
    # GPU_decode_number_list = GPU_decrypt_number_list.decode()
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------GPU with BatchEncode:-------------------")
    # start_time = time.time()
    # GPU_with_batch_decode_number_list = GPU_with_batch_decrypt_number_list.batch_decode(encoder.scaling, encoder.size, encoder.slot_mem_size, encoder.bit_width, encoder.sign_bits)
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))




def test_matrix_operation():
    row_vec_A = np.random.uniform(-1, 1, 1000)
    elements_num = row_vec_A.size
    row_vec_B = np.random.uniform(-1, 1, 1000)
    row_vec_A = row_vec_A.astype(np.float32)
    row_vec_B = row_vec_B.astype(np.float32)
    key_generator = PaillierEncrypt()
    key_generator.generate_key()
    '''Init encoder'''
    max_value, element_mem_size, encode_slot_mem, encode_sign_bits = 1, 24, 144, 40
    max_element_num = int(1024 / encode_slot_mem)
    split_num = int(np.ceil(len(row_vec_A) / max_element_num))
    encoder = BatchEncoder(max_value, element_mem_size, encode_slot_mem, encode_sign_bits, max_element_num)
    row_vec_used_in_gpu_A = np.hstack((row_vec_A, np.zeros(max_element_num * split_num - elements_num)))
    row_vec_used_in_cpu_A = row_vec_used_in_gpu_A.reshape(split_num, max_element_num)
    row_vec_used_in_gpu_B = np.hstack((row_vec_B, np.zeros(max_element_num * split_num - elements_num)))
    row_vec_used_in_cpu_B = row_vec_used_in_gpu_B.reshape(split_num, max_element_num)
    # '''CPU'''
    # print("Begin encoding and encrypting using CPU")
    # CPU_encode_num_list_A = [FixedPointNumber.encode(v) for v in row_vec_A]
    # CPU_encode_num_list_B = [FixedPointNumber.encode(v) for v in row_vec_B]
    # CPU_pen_list_A = [PaillierEncryptedNumber(key_generator.public_key, key_generator.public_key.raw_encrypt(v.encoding), v.exponent) for v in CPU_encode_num_list_A]
    # CPU_pen_list_B = [PaillierEncryptedNumber(key_generator.public_key, key_generator.public_key.raw_encrypt(v.encoding), v.exponent) for v in CPU_encode_num_list_B]
    # '''CPU with BatchEncode'''
    # print("Begin encoding and encrypting using CPU with BatchEncode")
    # CPU_with_batch_encode_number_list_A = [encoder.batchEncode(slot_number) for slot_number in row_vec_used_in_cpu_A]    # a list of BatchEncodeNumber
    # CPU_with_batch_encode_number_list_B = [encoder.batchEncode(slot_number) for slot_number in row_vec_used_in_cpu_B]    # a list of BatchEncodeNumber
    # CPU_with_batch_pen_list_A = [PaillierEncryptedNumber(key_generator.public_key, key_generator.public_key.raw_encrypt(v), 0) for v in CPU_with_batch_encode_number_list_A]
    # CPU_with_batch_pen_list_B = [PaillierEncryptedNumber(key_generator.public_key, key_generator.public_key.raw_encrypt(v), 0) for v in CPU_with_batch_encode_number_list_B]
    '''GPU'''
    fpn_store_A = FPN_store.init_from_arr(row_vec_A, key_generator.public_key.n, key_generator.public_key.max_int)
    fpn_store_B = FPN_store.init_from_arr(row_vec_B, key_generator.public_key.n, key_generator.public_key.max_int)
    pen_store_A = fpn_store_A.encrypt(key_generator.public_key)
    pen_store_A = pen_store_A.obfuscation()
    pen_store_B = fpn_store_B.encrypt(key_generator.public_key)
    pen_store_B = pen_store_B.obfuscation()
    '''GPU with BatchEncode'''
    encrypter = BatchEncryption()
    fpn_with_batch_store_A = FPN_store.batch_encode(row_vec_used_in_gpu_A, encoder.scaling, encoder.size, encoder.slot_mem_size, encoder.bit_width, encoder.sign_bits, key_generator.public_key)
    fpn_with_batch_store_B = FPN_store.batch_encode(row_vec_used_in_gpu_B, encoder.scaling, encoder.size, encoder.slot_mem_size, encoder.bit_width, encoder.sign_bits, key_generator.public_key)
    pen_with_batch_store_A = encrypter.gpuBatchEncrypt(fpn_with_batch_store_A, encoder.scaling, encoder.size, key_generator.public_key)
    pen_with_batch_store_B = encrypter.gpuBatchEncrypt(fpn_with_batch_store_B, encoder.scaling, encoder.size, key_generator.public_key)


    print("\n--------------------------------------ADD Test Report:--------------------------------------")
    # print("\n-------------------CPU:-------------------")
    # start_time = time.time()
    # res = [a + b for a, b in zip(CPU_pen_list_A, CPU_pen_list_B)]
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------CPU with BatchEncode:-------------------")
    # start_time = time.time()
    # res = [a + b for a, b in zip(CPU_with_batch_pen_list_A, CPU_with_batch_pen_list_B)]
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------GPU:-------------------")
    start_time = time.time()
    res = pen_store_A + pen_store_B
    stop_time = time.time()
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("Duration: ", stop_time - start_time)
    print("\n-------------------GPU with BatchEncode:-------------------")
    start_time = time.time()
    res = pen_with_batch_store_A.value + pen_with_batch_store_B.value
    stop_time = time.time()
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("Duration: ", stop_time - start_time)


    print("\n--------------------------------------MUL Test Report:--------------------------------------")
    # print("\n-------------------CPU:-------------------")
    # start_time = time.time()
    # cpu_res = [a * b for a, b in zip(CPU_pen_list_A, CPU_encode_num_list_B)]
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    # print("\n-------------------CPU with BatchEncode:-------------------")
    # coefficients_list = []
    # for split_idx in range(max_element_num):
    #     coefficients = [v[split_idx] for v in row_vec_used_in_cpu_B]
    #     coefficients = encoder.scalarEncode(coefficients)       # encode
    #     coefficients_list.append(coefficients)
    # # begin computation
    # start_time = time.time()
    # batch_num_list_in_cpu = [copy.deepcopy(CPU_with_batch_pen_list_A) for _ in range(max_element_num)]
    # for split_idx in range(max_element_num):
    #     batch_num_list_in_cpu[split_idx] = [a * b for a, b in zip(CPU_with_batch_pen_list_A, coefficients_list[split_idx])]
    # stop_time = time.time()
    # print("Duration: ", stop_time - start_time)
    # print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------GPU:-------------------")
    start_time = time.time()
    res = pen_store_A * fpn_store_B
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))
    print("\n-------------------GPU with BatchEncode:-------------------")
    coefficients_list = []
    for split_idx in range(max_element_num):
        coefficients = [v[split_idx] for v in row_vec_used_in_cpu_B]
        coefficients = FPN_store.quantization(coefficients, encoder.scaling, encoder.bit_width, encoder.sign_bits, key_generator.public_key)       # encode
        coefficients_list.append(coefficients)
    start_time = time.time()
    t1 = time.time()
    batch_num_list_in_gpu = [pen_with_batch_store_A.value.deep_copy() for _ in range(max_element_num)]     # copy
    t2 = time.time()
    print(t2 - t1)
    # cat
    # input_pen_store = batch_num_list_in_gpu[0]
    # input_fpn_store = coefficients_list[0]
    # for split_idx in range(1, max_element_num):
    #     input_pen_store = input_pen_store.cat(batch_num_list_in_gpu[split_idx], axis=1)
    #     input_fpn_store = input_fpn_store.cat(coefficients_list[split_idx], axis=1)
    # t1 = time.time()
    # print(t1 - t2)
    # input_pen_store = input_pen_store * input_fpn_store
    # t2 = time.time()
    # print(t2 - t1)

    # compute without cat
    res = [batch_num_list_in_gpu[split_idx] * coefficients_list[split_idx] for split_idx in range(max_element_num)]
    # gpu_with_batch_res = [a * b for a, b in zip(batch_num_list_in_gpu, coefficients_list)]    # linear execute multiplication
    stop_time = time.time()
    print("Duration: ", stop_time - start_time)
    print("Throughput: ", int(elements_num / (stop_time - start_time)))

def test_mul(pen, coefficient):
    return pen * coefficient

test_matrix_operation()