# from nodes.node import node
from copy import deepcopy
import torch
from sklearn.cluster import KMeans
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from pandas.plotting import parallel_coordinates

class server_class():
    def __init__(self, device):
        self.device = device
        self.test_metrics = []
        self.clustering = {'label':[], 'raw':[], 'center':[]}

    def assign_model(self, model):
        self.model = model
        self.model.to(self.device)

    def aggregate(self, nodes, idlist, weight_type='data_size'):
        aggregated_weights = self.model.state_dict()
        for j in aggregated_weights.keys():
            aggregated_weights[j] = torch.zeros(aggregated_weights[j].shape).to(self.device)
        sum_size = sum([nodes[i].data_size for i in idlist])
        for i in idlist:
            if weight_type == 'equal':
                weight = 1/len(idlist)
            elif weight_type == 'data_size':
                weight = nodes[i].data_size/sum_size
            for j in nodes[i].model.state_dict().keys():
                aggregated_weights[j] += nodes[i].model.state_dict()[j]*weight
        self.model.load_state_dict(aggregated_weights)
        return self.model
    
    def acc(self, nodes, idlist, weight_type='data_size'):
        global_test_metrics = [0]*2
        sum_size = sum([nodes[i].data_size for i in idlist])
        for i in idlist:
            if weight_type == 'equal':
                weight = 1/len(idlist)
            elif weight_type == 'data_size':
                weight = nodes[i].data_size/sum_size
            for j in range(len(global_test_metrics)):
                global_test_metrics[j] += weight*nodes[i].test_metrics[-1][j]
        print('GLOBAL Accuracy, Macro F1 is %.2f %%, %.2f %%' % (100*global_test_metrics[0], 100*global_test_metrics[1]))
        self.test_metrics.append(global_test_metrics)
               
    def distribute(self, nodes, idlist):
        for i in idlist:
            nodes[i].model.load_state_dict(self.model.state_dict())

    def client_sampling(self, frac, distribution):
        pass

    def test(self, test_loader):
        correct = 0
        total = 0
        with torch.no_grad():
            for data in test_loader:
                inputs, labels = data
                inputs = inputs.to(self.device)
                labels = torch.flatten(labels)
                labels = labels.to(self.device, dtype = torch.long)
                outputs = self.model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        print('Accuracy on the %d test cases: %.2f %%' % (total, 100*correct / total))
        # torch.cuda.empty_cache()

    def model_similarity(model_repr_1, model_repr_2, repr='output'):
        if repr == 'output':
            self.similarity = (log(model_repr_1)-log(model_repr_2)).sum(axis=1).abs()

    def weighted_clustering(self, nodes, idlist, K, weight_type='data_size'):
        weight = []
        X = []
        sum_size = sum([nodes[i].data_size for i in idlist])
        # print(list(nodes[0].model.state_dict().keys()))
        for i in idlist:
            if weight_type == 'equal':
                weight.append(1/len(idlist))
            elif weight_type == 'data_size':
                weight.append(nodes[i].data_size/sum_size)
            X.append(np.array(torch.flatten(nodes[i].model.state_dict()[list(nodes[i].model.state_dict().keys())[-2]]).cpu()))
        # print(X, np.array(X).shape)
        kmeans = KMeans(n_clusters=K).fit(np.asarray(X), sample_weight= weight)
        labels = kmeans.labels_
        print(labels)
        for i in idlist:
            nodes[i].label = labels[i]
        self.clustering['label'].append(list(labels))
        # self.clustering['raw'].append(X)
        # self.clustering['center'].append(kmeans.cluster_centers_)

    def clustering_plot(self):
        # print(self.clustering)
        # self.clustering =[[1,1,2,2,3,3],[1,1,1,2,2,2],[1, 1, 1, 2, 2, 2],[1, 1, 1, 2, 2, 2]]
        col = [str(i) for i in range(len(self.clustering))]+['id']
        self.clustering.append(list(range(len(self.clustering[0]))))
        data= pd.DataFrame(np.array(self.clustering).T,columns= col)
        for i in data.columns:
            data[i]=data[i].apply(lambda x: str(x))
        # Make the plot
        parallel_coordinates(data, 'id', colormap=plt.get_cmap("Set2"))
        plt.show()
