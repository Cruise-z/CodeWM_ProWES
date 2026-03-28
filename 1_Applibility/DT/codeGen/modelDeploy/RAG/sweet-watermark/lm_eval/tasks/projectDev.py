# tasks/my_task.py
import json
from lm_eval.base import Task

class MyCustomTask(Task):
    DATASET_PATH = None  # Not needed if your dataset is not downloaded from the HuggingFace Hub
    DATASET_NAME = None  # Set to None if there is no subset

    def __init__(self, data_path="/home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/datasets/projectDev_java_temp.jsonl", **kwargs):
        super().__init__(stop_words=["<|endoftext|>"], requires_execution=False)
        self.data_path = data_path
        self._data = []
        self._load_data()

    def _load_data(self):
        """Load the JSONL data file."""
        with open(self.data_path, "r", encoding="utf-8") as f:
            for line in f:
                self._data.append(json.loads(line))

    def get_dataset(self):
        """Return the dataset."""
        return self._data

    def get_prompt(self, doc):
        """Build the prompt used for generation."""
        return f"{doc['prompt']}{doc['prefix']}"  # Use the 'prompt' + 'prefix' fields as model input

    def get_reference(self, doc):
        """Reference answer; if your dataset has no reference answers, you can return None or an empty string."""
        return doc["reference"]  # Use the 'reference' field as the reference answer

    def postprocess_generation(self, generation, idx):
        """Post-process the generated text."""
        return generation.strip()  # Additional processing logic can be added here

    def process_results(self, generations, references):
        """Compute evaluation metrics."""
        # If there is no reference answer, you can skip evaluation or compare
        # the generation against some other standard.
        # This keeps it simple: if there is no reference answer, return an empty result.
        return {"results": "No reference to evaluate"}
