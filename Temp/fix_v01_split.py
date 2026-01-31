from pathlib import Path

root = Path('/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/AI_datasets/yolo_ball_v01')
img = root / 'images'
lbl = root / 'labels'
meta = root / 'meta'

train_img = img / 'train'
val_img = img / 'val'
train_lbl = lbl / 'train'
val_lbl = lbl / 'val'
train_meta = meta / 'train'
val_meta = meta / 'val'

for d in [train_img, val_img, train_lbl, val_lbl]:
    d.mkdir(parents=True, exist_ok=True)
if meta.exists():
    train_meta.mkdir(parents=True, exist_ok=True)
    val_meta.mkdir(parents=True, exist_ok=True)

# Remove flat duplicates; move any stray flat files into train by default.
removed = 0
moved = 0

for p in img.glob('*.jpg'):
    if (train_img / p.name).exists() or (val_img / p.name).exists():
        p.unlink()
        removed += 1
    else:
        (train_img / p.name).write_bytes(p.read_bytes())
        p.unlink()
        moved += 1

for p in lbl.glob('*.txt'):
    if (train_lbl / p.name).exists() or (val_lbl / p.name).exists():
        p.unlink()
        removed += 1
    else:
        (train_lbl / p.name).write_bytes(p.read_bytes())
        p.unlink()
        moved += 1

if meta.exists():
    for p in meta.glob('*.meta.json'):
        if (train_meta / p.name).exists() or (val_meta / p.name).exists():
            p.unlink()
            removed += 1
        else:
            (train_meta / p.name).write_bytes(p.read_bytes())
            p.unlink()
            moved += 1

print(f'removed {removed} moved {moved}')
