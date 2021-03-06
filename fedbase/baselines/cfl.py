from fedbase.utils.data_loader import data_process, log
from fedbase.nodes.node import node
from fedbase.server.server import server_class
import torch
from torch.utils.data import DataLoader
import torch.optim as optim
from fedbase.model.model import CNNCifar, CNNMnist
import os
import sys
import inspect
from functools import partial


def run(dataset_splited, batch_size, num_nodes, model, objective, optimizer, global_rounds, local_steps, eps_1 = 0.4, eps_2 = 1.6, device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')):
    # dt = data_process(dataset)
    # train_splited, test_splited = dt.split_dataset(num_nodes, split['split_para'], split['split_method'])
    train_splited, test_splited, split_para = dataset_splited
    server = server_class(device)
    server.assign_model(model())

    nodes = [node(i, device) for i in range(num_nodes)]
    # local_models = [model() for i in range(num_nodes)]
    local_loss = [objective() for i in range(num_nodes)]

    for i in range(num_nodes):
        # data
        # print(len(train_splited[i]), len(test_splited[i]))
        nodes[i].assign_train(DataLoader(train_splited[i], batch_size=batch_size, shuffle=True))
        nodes[i].assign_test(DataLoader(test_splited[i], batch_size=batch_size, shuffle=False))
        # model
        # nodes[i].assign_model(local_models[i])
        # objective
        nodes[i].assign_objective(local_loss[i])
        # optim
        # nodes[i].assign_optim(optimizer(model().parameters()))

    # initialize parameters to nodes
    # server.distribute(nodes, list(range(num_nodes)))

    # initialize K cluster model
    cluster_models = [model() for i in range(K)]

    # train!
    for i in range(global_rounds):
        print('-------------------Global round %d start-------------------' % (i))
        # assign client to cluster
        assignment = [[] for _ in range(K)]
        for i in range(num_nodes):
            m = 0
            for k in range(1, K):
                # print(nodes[i].local_train_loss(cluster_models[m]), nodes[i].local_train_loss(cluster_models[k]))
                if nodes[i].local_train_loss(cluster_models[m])>=nodes[i].local_train_loss(cluster_models[k]):
                    m = k
            assignment[m].append(i)
            nodes[i].assign_model(cluster_models[m])
            nodes[i].assign_optim(optimizer(nodes[i].model.parameters()))
        print(assignment)

        # local update
        for i in range(num_nodes):
            nodes[i].local_update_steps(local_steps, partial(nodes[i].train_single_step))

        # server aggregation and distribution by cluster
        for k in range(K):
            if len(assignment[k])>0:
                server.aggregate(nodes, assignment[k])
                server.distribute(nodes, assignment[k])
                cluster_models[k] = server.model

        # test accuracy
        for i in range(num_nodes):
            nodes[i].local_test()
        server.acc(nodes, list(range(num_nodes)))

    # log
    log(os.path.basename(__file__)[:-3] + '_' + str(K) + '_' + split_para, nodes, server)