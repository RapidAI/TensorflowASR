
import numpy as np
import os
from utils.text_featurizers import TextFeaturizer
from utils.speech_featurizers import SpeechFeaturizer
from AMmodel.conformer import ConformerTansducer,ConformerCTC,ConformerLAS
import logging

class AM():
    def __init__(self,config):
        self.config = config
        self.update_model_type()
        self.speech_config= config['speech_config']
        self.text_config=config['decoder_config']
        self.model_config=config['model_config']
        self.text_feature=TextFeaturizer(self.text_config)
        self.speech_feature=SpeechFeaturizer(self.speech_config)
        self.model_config.update({'vocabulary_size':self.text_feature.num_classes})

    def update_model_type(self):
        if 'CTC' in self.config['model_config']['name']:
            self.config['decoder_config'].update({'model_type': 'CTC'})
        elif 'LAS' in self.config['model_config']['name']:
            self.config['decoder_config'].update({'model_type': 'LAS'})
        else:
            self.config['decoder_config'].update({'model_type': 'Transducer'})

    def load_model(self,training=True):
        if self.model_config['name']=='ConformerTransducer':
            self.model=ConformerTansducer(**self.model_config)
        elif self.model_config['name']=='ConformerCTC':
            self.model=ConformerCTC(**self.model_config)
        elif self.model_config['name']=='ConformerLAS':
            self.config['model_config']['LAS_decoder'].update({'n_classes': self.text_feature.num_classes})
            self.config['model_config']['LAS_decoder'].update({'startid': self.text_feature.start})
            self.model=ConformerLAS(self.config['model_config'], training=training)
        else:
            raise ('not in supported model list')
        self.model.add_featurizers(self.text_feature)
        f,c=self.speech_feature.compute_feature_dim()
        if self.text_config['model_type'] != 'LAS':
            self.model._build([1,80,f,c])
        else:
            self.model._build([1, 80, f, c], training)
        try:
            self.load_checkpoint(self.config)
        except:
            logging.info('lm loading model failed.')
    def decode_result(self,word):
        de=[]
        for i in word:
            if i!=self.text_feature.stop:
                de.append(self.text_feature.index_to_token[int(i)])
            else:
                break
        return de
    def predict(self,fp,return_string_list=True):
        if '.pcm' in fp:
            data=np.fromfile(fp,'int16')
            data=np.array(data,'float32')
            data/=32768
        else:
            data = self.speech_feature.load_wav(fp)

        mel=self.speech_feature.extract(data)
        mel=np.expand_dims(mel,0)
        result=self.model.recognize(mel)[0]

        if return_string_list:
            result=result.numpy().argmax(-1)
            result=self.decode_result(result)
        return result

    def load_checkpoint(self,config):
        """Load checkpoint."""

        self.checkpoint_dir = os.path.join(config['learning_config']['running_config']["outdir"], "checkpoints")
        files = os.listdir(self.checkpoint_dir)
        files.sort(key=lambda x: int(x.split('_')[-1].replace('.h5', '')))
        self.model.load_weights(os.path.join(self.checkpoint_dir, files[-1]))