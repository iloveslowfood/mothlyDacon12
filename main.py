import os
import argparse
from tqdm import tqdm

import numpy as np
import torch
from torch import nn, optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from core.configuration.config import Config
from core.model.cnn import VanillaCNN
from core.evaluation.evaluation import evaluate
from core.load.load_data import dirtyMNISTDataset


def get_config():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--model_type', default='VanillaCNN', type=str)
    parser.add_argument("--epochs", default=3, type=int)
    parser.add_argument("--batch_size", default=16, type=int)
    parser.add_argument("--lr", default=1e-3, type=float)

    args = parser.parse_args()

    config = Config(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu"),
    )
    return config


def get_data(batch_size: int = 16):
    print(f"Getting Data...", end="\t")

    # transform = transforms.Compose([transforms.Grayscale(), transforms.ToTensor()])
    train_dataset = dirtyMNISTDataset(mode="train", transform=None)
    valid_dataset = dirtyMNISTDataset(mode="valid", transform=None)

    train_loader = DataLoader(
        dataset=train_dataset, batch_size=batch_size, shuffle=True
    )
    valid_loader = DataLoader(
        dataset=valid_dataset, batch_size=batch_size, shuffle=True
    )
    print("Data loaded.")
    return train_loader, valid_loader


def get_model(lr: float, device: str):
    model = VanillaCNN().to(device)
    loss_function = nn.MultiLabelSoftMarginLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    return model, loss_function, optimizer


def train_model(
    model: nn.Module,
    loss_function,
    optimizer,
    train_loader: DataLoader,
    valid_loader: DataLoader,
    epochs: int,
    batch_size: int,
    device: str,
    checkpoint: str = "checkpoint/",
):
    print("Train start...")
    model.train()
    print_every = 1

    # train phase
    for idx, epoch in enumerate(range(epochs)):

        loss_val_sum = 0

        for batch in tqdm(train_loader):
            X = batch["image"].float().to(device)
            y_true = batch["label"].float().to(device)

            if len(X.size()) == 3:  # channel=1
                N, H, W = X.size()
                C = 1
            else:  # channel=3
                N, C, H, W = X.size()

            y_pred = model.forward(X.view(-1, C, H, W).float().to(device))
            loss = loss_function(y_pred, y_true)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            loss_val_sum += loss

        if ((epoch % print_every) == 0) or (epoch == (epochs - 1)):
            loss_val_avg = loss_val_sum / len(train_loader)
            accr_val = evaluate(model=model, data_iter=valid_loader, device=device)
            print(
                f"epoch:[{epoch+1}/{epochs}] cost:[{loss_val_avg:.3f}] test_accuracy:[{accr_val:.3f}]"
            )

        checkpoint_name = os.path.join(checkpoint, f'VanillaCNN_{idx}.pt')
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": loss_val_avg,
            },
            checkpoint_name,
        )

    print("Train finished.")



if __name__ == "__main__":
    print('Getting arguments...', end='\t')
    config = get_config()
    print('finished.')
    
    train_loader, valid_loader = get_data(batch_size=config.batch_size)
    model, loss_function, optimizer = get_model(lr=config.lr, device=config.device)

    train_model(
        model=model,
        loss_function=loss_function,
        optimizer=optimizer,
        train_loader=train_loader,
        valid_loader=valid_loader,
        epochs=config.epochs,
        batch_size=config.batch_size,
        device=config.device,
    )
