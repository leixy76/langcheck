from typing import List, Tuple

import torch
from transformers import BertForSequenceClassification, BertTokenizer


def load_checkpoint(
    device: str
) -> Tuple[BertForSequenceClassification, BertTokenizer, List[str]]:
    checkpoint_url = "https://github.com/unitaryai/detoxify/releases/download/v0.1-alpha/toxic_original-c1212f89.ckpt"
    loaded = torch.hub.load_state_dict_from_url(checkpoint_url,
                                                map_location=device)
    class_names = loaded["config"]["dataset"]["args"]["classes"]
    change_names = {
        "toxic": "toxicity",
        "identity_hate": "identity_attack",
        "severe_toxic": "severe_toxicity",
    }
    class_names = [change_names.get(cl, cl) for cl in class_names]
    model_type = loaded["config"]["arch"]["args"]["model_type"]
    num_classes = loaded["config"]["arch"]["args"]["num_classes"]
    state_dict = loaded["state_dict"]

    model = BertForSequenceClassification.from_pretrained(
        pretrained_model_name_or_path=model_type,
        num_labels=num_classes,
        state_dict=state_dict)
    tokenizer = BertTokenizer.from_pretrained(model_type)

    # For type check
    assert isinstance(model, BertForSequenceClassification)
    return model, tokenizer, class_names


class Detoxify:
    '''Class for loading the Detoxify model. This is a modified version of the
    Detoxify class in
    https://github.com/unitaryai/detoxify/blob/master/detoxify/detoxify.py.

    Args:
        device: The device on which the model is loaded (default 'cpu')

    Returns:
        results: dictionary of output scores for each class
    '''

    def __init__(self, device: str = "cpu"):
        self.model, self.tokenizer, self.class_names = load_checkpoint(device)
        self.device = device
        self.model.to(self.device)  # type: ignore

    @torch.no_grad()
    def predict(self, text):
        self.model.eval()
        inputs = self.tokenizer(text,
                                return_tensors="pt",
                                truncation=True,
                                padding=True).to(self.model.device)
        out = self.model(**inputs)[0]
        scores = torch.sigmoid(out).cpu().detach().numpy()
        results = {}
        for i, cla in enumerate(self.class_names):
            results[cla] = (scores[0][i] if isinstance(text, str) else [
                scores[ex_i][i].tolist() for ex_i in range(len(scores))
            ])
        return results
