"""
Train a Type Predictor (TP) model using CodeSearchNet Java dataset.
The trained model predicts the next lexical token type based on a sequence of previous token types.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
import json
import argparse
from pathlib import Path
from tqdm import tqdm
from pygments.lexers import PythonLexer, GoLexer, JavaLexer, JavascriptLexer, PhpLexer
from pygments.token import STANDARD_TYPES
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LSTMModel(nn.Module):
    """LSTM-based type predictor model."""
    def __init__(self, vocab_size, embed_size, hidden_size, output_size):
        super(LSTMModel, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size)
        self.lstm = nn.LSTM(embed_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        embedded = self.embedding(x)
        _, (hn, cn) = self.lstm(embedded)
        output = self.fc(hn[-1, :, :])
        return output


class CodeTypeDataset(Dataset):
    """
    Dataset for training type predictor.
    Loads code from JSON files and converts to lexical token type sequences.
    """
    def __init__(self, json_files, lexer, nonterminal2id, seq_length=30):
        self.lexer = lexer
        self.nonterminal2id = nonterminal2id
        self.seq_length = seq_length
        self.vocab_size = len(nonterminal2id)  # Store vocab size for model initialization
        self.sequences = []

        for json_file in json_files:
            logger.info(f"Loading data from {json_file}")
            try:
                # determine number of lines first so we can show a complete progress bar
                with open(json_file, 'r', encoding='utf-8') as f:
                    total_lines = sum(1 for _ in f)

                with open(json_file, 'r', encoding='utf-8') as f:
                    for line in tqdm(f, total=total_lines,
                                     desc=f"Reading {Path(json_file).name}",
                                     unit="lines"):
                        try:
                            obj = json.loads(line)
                            code = obj.get('code', '')
                            if code:
                                self._process_code(code)
                        except json.JSONDecodeError:
                            # skip malformed lines
                            continue
            except Exception as e:
                logger.warning(f"Error processing {json_file}: {e}")
                continue

    def _process_code(self, code):
        """Convert code to lexical token type sequence."""
        try:
            tokens = list(self.lexer.get_tokens(code))
            lex_array = []

            for token_type, value in tokens:
                try:
                    token_id = self.nonterminal2id[STANDARD_TYPES[token_type]]
                    lex_array.append(token_id)
                except KeyError:
                    continue

            # Create sliding window sequences
            if len(lex_array) > self.seq_length:
                for i in range(len(lex_array) - self.seq_length):
                    seq = lex_array[i:i + self.seq_length]
                    if len(seq) == self.seq_length:
                        self.sequences.append(torch.tensor(seq, dtype=torch.long))
        except Exception as e:
            logger.debug(f"Error processing code: {e}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx]
        # Input: all but last token, Target: last token
        return seq[:-1], seq[-1]


def collate_fn(batch):
    """Collate function for DataLoader."""
    inputs, targets = zip(*batch)
    inputs = torch.stack(inputs)
    targets = torch.tensor(targets, dtype=torch.long)
    return inputs, targets


def train_epoch(model, dataloader, optimizer, criterion, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    pbar = tqdm(dataloader, desc="Training")
    for inputs, targets in pbar:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        _, predicted = torch.max(outputs.data, 1)
        total += targets.size(0)
        correct += (predicted == targets).sum().item()

        pbar.set_postfix({'loss': f'{total_loss / (pbar.n + 1):.4f}'})

    avg_loss = total_loss / len(dataloader)
    accuracy = 100 * correct / total

    return avg_loss, accuracy


def evaluate(model, dataloader, criterion, device):
    """Evaluate on validation set."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in tqdm(dataloader, desc="Validating"):
            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            total_loss += loss.item()

            _, predicted = torch.max(outputs.data, 1)
            total += targets.size(0)
            correct += (predicted == targets).sum().item()

    avg_loss = total_loss / len(dataloader)
    accuracy = 100 * correct / total

    return avg_loss, accuracy


def main(args):
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Setup lexer based on language
    lexer_map = {
        'python': PythonLexer,
        'java': JavaLexer,
        'go': GoLexer,
        'javascript': JavascriptLexer,
        'php': PhpLexer
    }

    if args.language not in lexer_map:
        raise ValueError(f"Unsupported language: {args.language}")

    lexer = lexer_map[args.language]()

    # Create nonterminal2id mapping
    nonterminal2id = {nonterminal: i for i, nonterminal in enumerate(STANDARD_TYPES.values())}
    num_classes = len(nonterminal2id)

    logger.info(f"Number of lexical token types: {num_classes}")

    # Load datasets
    json_files = list(Path(args.data_dir).glob('**/*.jsonl'))
    if not json_files:
        raise ValueError(f"No JSONL files found in {args.data_dir}")

    logger.info(f"Found {len(json_files)} JSON files")

    dataset = CodeTypeDataset(
        json_files,
        lexer,
        nonterminal2id,
        seq_length=args.seq_length
    )

    logger.info(f"Total sequences: {len(dataset)}")

    if len(dataset) < 100:
        logger.warning("Dataset too small, may not train effectively")

    # Split into train and validation
    train_size = int(0.9 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset,
        [train_size, val_size]
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=args.num_workers
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=args.num_workers
    )

    # Build model
    model = LSTMModel(
        vocab_size=dataset.vocab_size,  # Use actual vocabulary size from dataset
        embed_size=args.embed_size,
        hidden_size=args.hidden_size,
        output_size=num_classes
    )
    model.to(device)

    logger.info(f"Model parameters: embed_size={args.embed_size}, hidden_size={args.hidden_size}")

    # Setup optimizer and loss
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    criterion = nn.CrossEntropyLoss()
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

    # Training loop
    best_val_acc = 0.0
    patience_counter = 0

    for epoch in range(args.epochs):
        logger.info(f"\n{'='*60}")
        logger.info(f"Epoch {epoch + 1}/{args.epochs}")
        logger.info(f"{'='*60}")

        train_loss, train_acc = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)

        logger.info(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        logger.info(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")

        scheduler.step()

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            model_path = Path(args.output_dir) / f"lstm_model_{args.language}.pth"
            torch.save(model.state_dict(), model_path)
            logger.info(f"Best model saved to {model_path}")
        else:
            patience_counter += 1

        # Early stopping
        if patience_counter >= args.patience:
            logger.info(f"Early stopping after {epoch + 1} epochs")
            break

    logger.info("\nTraining completed!")
    logger.info(f"Best validation accuracy: {best_val_acc:.2f}%")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train Type Predictor Model')

    # Data arguments
    parser.add_argument('--data_dir', type=str, required=True,
                        help='Path to CodeSearchNet JSONL files')
    parser.add_argument('--language', type=str, default='java',
                        choices=['python', 'java', 'go', 'javascript', 'php'],
                        help='Programming language')
    parser.add_argument('--seq_length', type=int, default=30,
                        help='Sequence length for training')

    # Model arguments
    parser.add_argument('--embed_size', type=int, default=64,
                        help='Embedding size')
    parser.add_argument('--hidden_size', type=int, default=128,
                        help='Hidden size of LSTM')

    # Training arguments
    parser.add_argument('--batch_size', type=int, default=128,
                        help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=0.001,
                        help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-5,
                        help='Weight decay')
    parser.add_argument('--epochs', type=int, default=20,
                        help='Number of epochs')
    parser.add_argument('--patience', type=int, default=3,
                        help='Early stopping patience')

    # Other arguments
    parser.add_argument('--device', type=str, default='cuda',
                        help='Device to use')
    parser.add_argument('--num_workers', type=int, default=4,
                        help='Number of workers for data loading')
    parser.add_argument('--output_dir', type=str, default='.',
                        help='Output directory for model')

    args = parser.parse_args()

    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    main(args)
