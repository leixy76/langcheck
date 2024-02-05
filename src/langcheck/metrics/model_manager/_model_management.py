import os
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Union

import pandas as pd
import requests
from omegaconf import OmegaConf
from sentence_transformers import SentenceTransformer
from tabulate import tabulate
from transformers.models.auto.modeling_auto import (  # NOQA:E501
    AutoModelForSeq2SeqLM, AutoModelForSequenceClassification)
from transformers.models.auto.tokenization_auto import AutoTokenizer

from ._model_loader import (load_auto_model_for_seq2seq,
                            load_auto_model_for_text_classification,
                            load_sentence_transformers)

LOADER_MAP = {
    "load_sentence_transformers":
        load_sentence_transformers,
    "load_auto_model_for_text_classification":
        load_auto_model_for_text_classification,  # NOQA:E501
    "load_auto_model_for_seq2seq":
        load_auto_model_for_seq2seq
}
VALID_LOADER_FUNCTION = LOADER_MAP.keys()  # NOQA:E501
VALID_METRICS = [
    'semantic_similarity', 'sentiment', 'toxicity', 'factual_consistency'
]

VALID_METRIC_ATTRIBUTE = [
    'model_revision', 'model_revision', 'loader', 'tokenizer_name'
]
VALID_LANGUAGE = ['zh']


def check_model_availability(model_name: str, revision: Optional[str]):
    # TODO: add local cached model availability check for offline environment
    if revision is None:
        url = f"https://huggingface.co/api/models/{model_name}"
    else:
        url = f"https://huggingface.co/api/models/{model_name}/revision/{revision}"  # NOQA:E501
    response = requests.get(url, timeout=(1.0, 1.0))
    return response.status_code == 200


class ModelManager:
    '''
    A class to manage different models for multiple languages in LangCheck.
    This class allows setting and retrieving different model names (like
    sentiment_model, semantic_similarity_model, etc.) for each language.
    It also supports loading model configurations from a file.
    '''

    def __init__(self):
        '''
        Initializes the ModelConfig with empty model dictionaries for each
        language.
        '''
        self.config = OmegaConf.create()
        cwd = os.path.dirname(__file__)
        default_config_file_path = os.path.join(cwd, "config",
                                                "metric_config.yaml")
        self.__load_config(default_config_file_path)

    def __load_config(self, path: str):
        conf = OmegaConf.load(path)

        for lang, lang_conf in conf.items():
            for metric_name, metric_conf in lang_conf.items():
                # check model availbility, if key not in conf
                # omega conf will return None in default
                self.__set_model_for_metric(language=lang,   # type: ignore  # NOQA:E501
                                            metric=metric_name,
                                            **metric_conf)
        print('Configuration Load Successed!')

    @lru_cache
    def fetch_model(
        self, language: str, metric: str
    ) -> Union[Tuple[AutoTokenizer, AutoModelForSequenceClassification], Tuple[
            AutoTokenizer, AutoModelForSeq2SeqLM], SentenceTransformer]:
        '''
        Return the model used for the given metric and language.

        Args:
            language: The language for which to get the model
            metric_type: The metric name
        '''
        if language in self.config:
            if metric in self.config[language]:
                # Deep copy the confguration so that changes to `config` would
                # not affect the original `self.config`.
                config = deepcopy(self.config[language][metric])
                # Get model name, model loader type
                loader_func = config.pop('loader_func')
                loader = LOADER_MAP[loader_func]
                return loader(**config)
            else:
                raise KeyError(f'Metric {metric} not supported yet.')
        else:
            raise KeyError(f'Language {language} not supported yet')

    @staticmethod
    def validate_config(config, language='all', metric='all'):
        '''
        Validate configuration.

        Args:
            language: The name of the language. Defaults to 'all'.
            metric: The name of the metric. Defaults to 'all'.
        '''
        config = deepcopy(config)
        for lang, lang_setting in config.items():
            if language != 'all' and lang != language:
                continue
            for metric_name, model_setting in lang_setting.items():
                if metric != 'all' and metric_name != metric:
                    continue
                # If model name not set
                if 'model_name' not in model_setting:
                    raise KeyError(
                        f'{lang} metrics {metric_name} need a model, but found None!'  # NOQA:E501
                    )
                if 'loader_func' not in model_setting:
                    raise KeyError(
                        f'Metrics {metric_name} need a loader, but found None!'  # NOQA:E501
                    )
                # Check if the model and revision is available on
                # Hugging Face Hub
                model_name = model_setting.pop('model_name')
                revision = model_setting.pop('revision', None)
                loader_func = model_setting.pop('loader_func', None)
                if loader_func not in VALID_LOADER_FUNCTION:
                    raise ValueError(
                        f'loader type should in {VALID_LOADER_FUNCTION}')
                if not check_model_availability(model_name, revision):
                    raise ValueError(
                        f'Cannot find {model_name} with {revision} and Huggingface Hub'  # NOQA:E501
                    )

    def __set_model_for_metric(self, language: str, metric: str,
                               model_name: str, loader_func: str, **kwargs):
        '''
        Set model for specified metric in specified language.

        Args:
            language: The name of the language
            metric: The name of the evaluation metrics
            model_name: The name of the model
            loader: The loader of the model
            tokenizer_name: (Optional) The name of the tokenizer
            revision: (Optional) A version string of the model
        '''
        config_copy = deepcopy(self.config)
        try:
            if language not in VALID_LANGUAGE:
                raise KeyError('Language {language} not supported yet')

            if metric not in VALID_METRICS:
                raise KeyError('Language {language} not supported {metric} yet')

            # initialize configuration structure if it is empty.
            if self.config.get(language) is None:
                self.config[language] = {}
            if self.config.get(language).get(metric) is None:
                self.config[language][metric] = {}

            detail_config = self.config[language][metric]
            # set metric attribute
            detail_config['loader_func'] = loader_func
            detail_config['model_name'] = model_name
            # If tokenizer_name is different from model_name
            tokenizer_name = kwargs.pop('tokenizer_name', None)
            if tokenizer_name:
                detail_config['tokenizer_name'] = tokenizer_name
            # If model's revision is pinned
            revision = kwargs.pop('model_revision', None)
            if revision:
                detail_config['revision'] = revision
            # Validate the change
            if ModelManager.validate_config(self.config,
                                            language=language,
                                            metric=metric):
                # Clear the LRU cache to make the config change reflected
                # immediately
                self.fetch_model.cache_clear()
        except (ValueError, KeyError) as err:
            # Trace back the configuration
            self.config = config_copy
            raise err

    def list_current_model_in_use(self, language='all', metric='all'):
        '''
        List the models currently in use.

        Args:
            language: The abbrevation name of language
            metric: The evaluation metric name
        '''
        df = pd.DataFrame.from_records(
            [(lang, metric_name, key, value)
             for lang, lang_model_settings in self.config.items()
             for metric_name, model_settings in lang_model_settings.items()
             for key, value in model_settings.items()],
            columns=['language', 'metric_name', 'attribute', 'value'])
        # The code below would generate a dataframe:
        # |index| language | metric_name | loader | model_name | revision |
        # |.....|..........|.............|........|............|..........|
        df_pivot = df.pivot_table(index=['language', 'metric_name'],
                                  columns="attribute",
                                  values="value",
                                  aggfunc='first').reset_index().rename_axis(
                                      None, axis=1)
        df_pivot.columns = [
            'language', 'metric_name', 'loader', 'model_name', 'revision'
        ]

        if language == 'all' and metric == 'all':
            print(
                tabulate(df_pivot, headers=df_pivot.columns, tablefmt="github"))  # type: ignore  # NOQA:E501
        else:
            if language != "all":
                df_pivot = df_pivot.loc[df_pivot.language == language]
            if metric != 'all':
                df_pivot = df_pivot.loc[df_pivot.metric_name == metric]
            print(
                tabulate(df_pivot, headers=df_pivot.columns,  # type: ignore  # NOQA:E501
                         tablefmt="github"))
