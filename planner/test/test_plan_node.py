import sys, math, time
from federatedml.FATE_Engine.python.BatchPlan.planner.plan_node import PlanNode
from federatedml.FATE_Engine.python.BatchPlan.planner.batch_plan import BatchPlan
from federatedml.FATE_Engine.python.BatchPlan.storage.data_store import DataStorage
from federatedml.FATE_Engine.python.BatchPlan.encryption.encrypt import BatchEncryption

import numpy as np

def init_batch_plan_from_matrix():
    data_store = DataStorage()
    myBatchPlan = BatchPlan(data_store, vector_mem_size=1024, element_mem_size=64)
    matrixA = np.random.rand(4,3)
    print(matrixA)
    myBatchPlan.fromMatrix(matrixA, True)
    print("matrix shape: " + str(myBatchPlan.matrix_shape))
    print("BatchPlan typology: ")
    myBatchPlan.printBatchPlan()
    myBatchPlan.assignVector()
    print("each root node:")
    for root in myBatchPlan.root_nodes:
        print("batch data: " + str(root.getBatchData()))
        print("batch shape: " + str(root.getShape()))

def matrix_add():
    data_store = DataStorage()
    myBatchPlan = BatchPlan(data_store, vector_mem_size=1024, element_mem_size=64)
    matrix_list = []
    for i in range(4):
        matrix_list.append(np.random.rand(4,3))
    print("\n-------------------Input Matrix: -------------------")
    for matrix in matrix_list:
        print(matrix)
    myBatchPlan.fromMatrix(matrix_list[0], True)
    myBatchPlan.matrixAdd([matrix_list[1], matrix_list[2]], [False, False])
    myBatchPlan.matrixAdd([matrix_list[3]], [False])
    print("BatchPlan typology")
    myBatchPlan.printBatchPlan()
    print("\n-------------------Begin to exec Batch Plan.-------------------")
    outputs = myBatchPlan.serialExec()
    row_num, col_num = myBatchPlan.matrix_shape
    output_matrix = np.zeros(myBatchPlan.matrix_shape)
    for row_id in range(row_num):
        output_matrix[row_id, :] = outputs[row_id]
    print("\n-------------------Batch Plan output:-------------------")
    print(output_matrix)
    print("\n-------------------Numpy output:-------------------")
    result = matrix_list[0]
    for i in range(1, len(matrix_list)):
        result += matrix_list[i]
    print(result)

    if np.allclose(output_matrix, result):
        print("\n-------------------Test Pass!-------------------")
    else:
        print("\n-------------------Test Fail-------------------")
        print(output_matrix == result)

def matrix_mul():
    data_store = DataStorage()
    myBatchPlan = BatchPlan(data_store, vector_mem_size=1024, element_mem_size=64)
    matrixA = np.random.rand(1, 10000)
    print("\n-------------------Matrix A: -------------------")
    print(matrixA)
    matrixB = np.random.rand(10000,20)
    print("\n-------------------Matrix B: -------------------")
    print(matrixB)
    myBatchPlan.fromMatrix(matrixA, True)
    myBatchPlan.matrixMul([matrixB])
    print("BatchPlan typology")
    myBatchPlan.printBatchPlan()
    print("\n-------------------Begin to exec Batch Plan.-------------------")
    outputs = myBatchPlan.serialExec()
    row_num, col_num = myBatchPlan.matrix_shape
    output_matrix = np.zeros(myBatchPlan.matrix_shape)
    for row_id in range(row_num):
        output_matrix[row_id, :] = outputs[row_id]
    print("\n-------------------Batch Plan output:-------------------")
    print(output_matrix)
    print("\n-------------------Numpy output:-------------------")
    result = matrixA.dot(matrixB)
    print(result)

    if np.allclose(output_matrix, result):
        print("\n-------------------Test Pass!-------------------")
    else:
        print("\n-------------------Test Fail-------------------")
        print(output_matrix == result)

def weaver():
    data_store = DataStorage()
    myBatchPlan = BatchPlan(data_store, vector_mem_size=1024, element_mem_size=16)
    # matrixA = np.random.randint(63, size=(1,8))
    # matrixB = np.random.randint(63, size=(1,8))
    # matrixC = np.random.randint(63, size=(8,2))
    matrixA = np.random.rand(1, 1000)
    matrixB = np.random.rand(1, 1000)
    matrixC = np.random.rand(1000, 2)


    print("\n-------------------Test Report:-------------------")
    myBatchPlan.fromMatrix(matrixA, True)
    print("In matrixA, max_slot_size of each vector is:", end=" ")
    for root in myBatchPlan.root_nodes:
        print(root.max_slot_size, end=" ")
    myBatchPlan.matrixAdd([matrixB], [False])
    print("\nAfter adding matrixB, max_slot_size of each vector is:", end=" ")
    for root in myBatchPlan.root_nodes:
        print(root.max_slot_size, end=" ")
    myBatchPlan.matrixMul([matrixC])
    print("\nAfter timing matrixC, max_slot_size of each vector is:", end=" ")
    for root in myBatchPlan.root_nodes:
        print(root.max_slot_size, end=" ")
    print("\n")
    idx = 0
    for root in myBatchPlan.root_nodes:
        vector_size = int(myBatchPlan.vector_mem_size / root.max_slot_size)
        print("Maximum compression rate in vector " + str(idx) + " is: " + str(vector_size))
        idx += 1
    print("\n-------------------Batch Plan before weave:-------------------")
    myBatchPlan.printBatchPlan()
    print("\n-------------------Batch Plan after weave:-------------------")
    myBatchPlan.weave()
    batch_scheme = myBatchPlan.getBatchScheme()
    max_element_num, split_num = batch_scheme[0]
    print("Element num in one vector: ", + max_element_num)
    print("Split num: ", + split_num)
    print(myBatchPlan.encode_slot_mem)
    print(myBatchPlan.encode_sign_bits)
    # myBatchPlan.printBatchPlan()

    print("\n-------------------Begin to exec Batch Plan.-------------------")
    # print(matrixC)
    col_num = matrixA.shape[1]
    encrypted_matrixA = np.hstack((matrixA, np.zeros((1, max_element_num * split_num - col_num))))
    encrypted_matrixA = encrypted_matrixA.reshape((split_num, max_element_num))
    encrypted_matrixA = [row_vec for row_vec in encrypted_matrixA]
    myBatchPlan.assignEncryptedVector(0, 0, encrypted_matrixA)
    outputs = myBatchPlan.serialExec()
    row_num, col_num = myBatchPlan.matrix_shape
    output_matrix = np.zeros(myBatchPlan.matrix_shape)
    for row_id in range(row_num):
        output_matrix[row_id, :] = outputs[row_id]
    print("\n-------------------Batch Plan output:-------------------")
    print(output_matrix)
    print("\n-------------------Numpy output:-------------------")
    result = matrixA + matrixB
    result = result.dot(matrixC)
    print(result)
    if np.allclose(output_matrix, result):
        print("\n-------------------Test Pass!-------------------")
    else:
        print("\n-------------------Test Fail-------------------")
        print(output_matrix == result)

def interaction():
    data_store = DataStorage()
    myBatchPlan = BatchPlan(data_store, vector_mem_size=1024, element_mem_size=64)
    matrixA = np.random.rand(1, 10)
    matrixB = np.random.rand(1, 10)
    matrixC = np.random.rand(10, 2)
    myBatchPlan.fromMatrix(matrixA, True)
    myBatchPlan.matrixAdd([matrixB], [False])
    myBatchPlan.matrixMul([matrixC])
    myBatchPlan.weave()
    print("\n-------------------Batch Plan after weave:-------------------")
    myBatchPlan.printBatchPlan()
    batch_scheme = myBatchPlan.getBatchScheme()
    print(batch_scheme)
    max_element_num, split_num = batch_scheme[0]
    encrypted_matrixA = np.random.rand(split_num, max_element_num)
    myBatchPlan.assignEncryptedVector(0, 0, encrypted_matrixA)
    print("\n-------------------Begin to exec Batch Plan.-------------------")
    # print(matrixC)
    outputs = myBatchPlan.parallelExec()
    row_num, col_num = myBatchPlan.matrix_shape
    output_matrix = np.zeros(myBatchPlan.matrix_shape)
    for row_id in range(row_num):
        output_matrix[row_id, :] = outputs[row_id]
    print("\n-------------------Batch Plan output:-------------------")
    print(output_matrix)
    print("\n-------------------Numpy output:-------------------")
    result = matrixA + matrixB
    result = result.dot(matrixC)
    print(result)
    if np.allclose(output_matrix, result):
        print("\n-------------------Test Pass!-------------------")
    else:
        print("\n-------------------Test Fail-------------------")
        print(output_matrix == result)
    

def split_sum():
    data_store = DataStorage()
    myBatchPlan = BatchPlan(data_store, vector_mem_size=1024, element_mem_size=24)
    matrixA = np.random.rand(1, 10)
    print("\n-------------------Test Report:-------------------")
    myBatchPlan.fromMatrix(matrixA, True)
    myBatchPlan.splitSum([[1, 3, 5]])
    myBatchPlan.weave()
    myBatchPlan.printBatchPlan()
    batch_scheme = myBatchPlan.getBatchScheme()
    max_element_num, split_num = batch_scheme[0]
    print("Element num in one vector: ", + max_element_num)
    print("Split num: ", + split_num)
    outputs = myBatchPlan.parallelExec()
    print(outputs[0])


split_sum()

