import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, Trainer, TrainingArguments
from datasets import load_dataset, Dataset
import pandas as pd
import json
from typing import List, Dict
import os
from sklearn.model_selection import train_test_split

class MedicalDatasetPreparation:
    def __init__(self, data_path: str = "medical_data"):
        self.data_path = data_path
        if not os.path.exists(data_path):
            os.makedirs(data_path)

    def prepare_custom_dataset(self, medical_qa_pairs: List[Dict]):
        """
        Convert medical QA pairs into a format suitable for training
        """
        dataset_dict = {
            'question': [],
            'context': [],
            'answer': [],
            'start_positions': [],
            'end_positions': []
        }

        for qa_pair in medical_qa_pairs:
            question = qa_pair['question']
            context = qa_pair['context']
            answer = qa_pair['answer']
            
            # Find the start and end positions of the answer in the context
            start_pos = context.find(answer)
            if start_pos != -1:
                end_pos = start_pos + len(answer)
                
                dataset_dict['question'].append(question)
                dataset_dict['context'].append(context)
                dataset_dict['answer'].append(answer)
                dataset_dict['start_positions'].append(start_pos)
                dataset_dict['end_positions'].append(end_pos)

        return Dataset.from_dict(dataset_dict)

class MedicalModelTrainer:
    def __init__(self, model_name: str = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForQuestionAnswering.from_pretrained(model_name)
        
    def preprocess_function(self, examples):
        questions = [q.strip() for q in examples["question"]]
        contexts = [c.strip() for c in examples["context"]]

        inputs = self.tokenizer(
            questions,
            contexts,
            max_length=384,
            truncation="only_second",
            stride=128,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding="max_length",
        )

        offset_mapping = inputs.pop("offset_mapping")
        sample_map = inputs.pop("overflow_to_sample_mapping")

        start_positions = []
        end_positions = []

        for i, offset in enumerate(offset_mapping):
            sample_idx = sample_map[i]
            start_char = examples["start_positions"][sample_idx]
            end_char = examples["end_positions"][sample_idx]
            sequence_ids = inputs.sequence_ids(i)

            # Find the start and end of the context
            idx = 0
            while sequence_ids[idx] != 1:
                idx += 1
            context_start = idx
            while sequence_ids[idx] == 1:
                idx += 1
            context_end = idx - 1

            # If the answer is not fully inside the context, label is (0, 0)
            if offset[context_start][0] > start_char or offset[context_end][1] < end_char:
                start_positions.append(0)
                end_positions.append(0)
            else:
                # Otherwise it's the start and end token positions
                idx = context_start
                while idx <= context_end and offset[idx][0] <= start_char:
                    idx += 1
                start_positions.append(idx - 1)

                idx = context_end
                while idx >= context_start and offset[idx][1] >= end_char:
                    idx -= 1
                end_positions.append(idx + 1)

        inputs["start_positions"] = start_positions
        inputs["end_positions"] = end_positions
        return inputs

    def train(self, train_dataset, eval_dataset, output_dir: str = "medical_qa_model"):
        training_args = TrainingArguments(
            output_dir=output_dir,
            evaluation_strategy="epoch",
            learning_rate=2e-5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            num_train_epochs=3,
            weight_decay=0.01,
            push_to_hub=False,
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
        )

        trainer.train()
        
        # Save the model
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)

def main():
    # Example medical QA pairs
    medical_qa_pairs = [
        {
            "question": "What are the symptoms of diabetes?",
            "context": "Common symptoms of diabetes include increased thirst, frequent urination, extreme hunger, unexplained weight loss, fatigue, blurred vision, and slow-healing sores.",
            "answer": "increased thirst, frequent urination, extreme hunger, unexplained weight loss, fatigue, blurred vision, and slow-healing sores"
        },
        # Add more medical QA pairs here
    ]

    # Prepare dataset
    dataset_prep = MedicalDatasetPreparation()
    dataset = dataset_prep.prepare_custom_dataset(medical_qa_pairs)
    
    # Split dataset
    train_size = 0.8
    train_dataset, eval_dataset = train_test_split(dataset, train_size=train_size)
    
    # Initialize and train model
    trainer = MedicalModelTrainer()
    trainer.train(train_dataset, eval_dataset)

if __name__ == "__main__":
    main()
