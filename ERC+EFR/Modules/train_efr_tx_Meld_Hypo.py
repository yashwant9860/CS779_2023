import torch
import torch.nn as nn
import torch.nn.functional as F
import tqdm
from torch.utils import data
from sklearn.metrics import classification_report
from sklearn.metrics import f1_score
from sklearn.metrics import confusion_matrix

from models import EFR_TX
from pickle_loader_meld_hypo import load_efr

batch_size = 128
seq_len = 5
seq2_len = seq_len
emb_size = 768
hidden_size = 768
batch_first = True

device = torch.device("cuda:2" if torch.cuda.is_available() else "cpu")
print(device)
print("________________________________________________________")

idx2utt, utt2idx, idx2emo, emo2idx, idx2speaker,\
        speaker2idx, weight_matrix, my_dataset_train, my_dataset_test,\
        global_speaker_info, speaker_dialogues, speaker_emotions, \
        speaker_indices, utt_len, global_speaker_info_test, speaker_dialogues_test, \
        speaker_emotions_test, speaker_indices_test, utt_len_test = load_efr()
    
def get_train_test_loader(bs):
    train_data_iter = data.DataLoader(my_dataset_train,batch_size=bs, shuffle=True, num_workers=3)
    test_data_iter = data.DataLoader(my_dataset_test,batch_size=bs, shuffle=True, num_workers=3)
    
    return train_data_iter, test_data_iter
    
def train(model, train_data_loader, epochs):
    class_weights2 = torch.FloatTensor(weights2).to(device)
    criterion2 = nn.CrossEntropyLoss(weight=class_weights2,reduction='none').to(device)
    
    optimizer = torch.optim.Adam(model.parameters(),lr=5e-8,weight_decay=1e-5)
    
    max_f1_2 = 0
   
    for epoch in tqdm.tqdm(range(epochs)):
        print("\n\n-------Epoch {}-------\n\n".format(epoch+1))
        model.train()
        
        avg_loss = 0
       
        y_true2 = []
        y_pred2 = []
            
        for i_batch, sample_batched in tqdm.tqdm(enumerate(train_data_loader)):
            dialogue_ids = sample_batched[0].tolist()
            inputs = sample_batched[1].to(device)
            targets2 = sample_batched[3].to(device)
            
            optimizer.zero_grad()
            
            _,outputs = model(inputs,dialogue_ids,utt_len)
            
            loss = 0
            for b in range(outputs.size()[0]):
              loss2 = 0
              
              for s in range(utt_len[dialogue_ids[b][0]]):
                pred2 = outputs[b][s]
                pred_flip = torch.argmax(F.softmax(pred2.to(device),-1),-1)
                
                truth2 = targets2[b][s]

                y_pred2.append(pred_flip.item())
                y_true2.append(truth2.long().to(device).item())

                pred2_ = torch.unsqueeze(pred2,0)
                truth2_ = torch.unsqueeze(truth2,0)
                
                loss2 += criterion2(pred2_,truth2_)
              loss2 /= utt_len[dialogue_ids[b][0]]
            
            loss += loss2
            loss /= outputs.size()[0]
            avg_loss += loss

            loss.backward()            
            optimizer.step()
            
        avg_loss /= len(train_data_loader)
        
        print("Average Loss = ",avg_loss)

        f1_2_cls,v_loss = validate(model, data_iter_test, epoch)
        print(f1_2_cls)
        if f1_2_cls > max_f1_2:
            print(f"Saving model at epoch {epoch} with f1-score"+str(f1_2_cls))
            max_f1_2 = f1_2_cls
            torch.save(model.state_dict(), "./efr_Meld_Hypo_{epc}_model_{f1}.pth".format(epc = epoch,f1=f1_2_cls))

    return model

def validate(model, test_data_loader,epoch):
    print("\n\n***VALIDATION ({})***\n\n".format(epoch))
    
    class_weights2 = torch.FloatTensor(weights2).to(device)
    criterion2 = nn.CrossEntropyLoss(weight=class_weights2,reduction='none').to(device)

    model.eval()

    with torch.no_grad():
      avg_loss = 0
      y_true2 = []
      y_pred2 = []

      for i_batch, sample_batched in tqdm.tqdm(enumerate(test_data_loader)):
            dialogue_ids = sample_batched[0].tolist()           
            inputs = sample_batched[1].to(device)
            targets2 = sample_batched[3].to(device)
                       
            _,outputs = model(inputs,dialogue_ids,utt_len_test)
            
            loss = 0
            for b in range(outputs.size()[0]):
              loss2 = 0
              
              for s in range(utt_len_test[dialogue_ids[b][0]]):
                pred2 = outputs[b][s]
                pred_flip = torch.argmax(F.softmax(pred2.to(device),-1),-1)
                
                truth2 = targets2[b][s]

                y_pred2.append(pred_flip.item())
                y_true2.append(truth2.long().to(device).item())

                pred2_ = torch.unsqueeze(pred2,0)
                truth2_ = torch.unsqueeze(truth2,0)
                
                loss2 += criterion2(pred2_,truth2_)
              loss2 /= utt_len_test[dialogue_ids[b][0]]
            
            loss += loss2
            loss /= outputs.size()[0]
            avg_loss += loss

      avg_loss /= len(test_data_loader)

      class_report = classification_report(y_true2,y_pred2)
      conf_mat2 = confusion_matrix(y_true2,y_pred2)

      print(class_report)
      print("Confusion Matrix: \n",conf_mat2)
    
      f1 = f1_score(y_true2,y_pred2)
      return f1,avg_loss

nclass = 2
emsize = 768
nhid = 768
nlayers = 6
nhead = 2
dropout = 0.2
model = EFR_TX(weight_matrix, utt2idx, nclass, emsize, nhead, nhid, nlayers, device, dropout).to(device)

weights2 = [1.0, 1.0]
data_iter_train, data_iter_test = get_train_test_loader(batch_size)
# model = train(model, data_iter_train, epochs = 1000)

model.load_state_dict(torch.load("efr_Meld_Hypo/efr_Meld_Hypo_183_model_0.48753016894609813.pth"))
validate(model, data_iter_test, 1)

