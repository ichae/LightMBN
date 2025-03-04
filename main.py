import data_v1
import data_v2
from loss import make_loss
from model import make_model
from optim import make_optimizer, make_scheduler
# import engine_v1
# import engine_v2
import engine_v3
import os.path as osp
from option import args
import utils.utility as utility
from utils.model_complexity import compute_model_complexity
from torch.utils.collect_env import get_pretty_env_info
import yaml
import torch

#
parser = argparse.ArgumentParser(description="ReID Baseline Inference")
parser.add_argument("--config_file", default="", help="path to config file", type=str)
parser.add_argument("opts", help="Modify config options using the command-line", default=None,
                    nargs=argparse.REMAINDER)

args = parser.parse_args()

if args.config_file != "":
    cfg.merge_from_file(args.config_file)

cfg.merge_from_list(args.opts)
cfg.freeze()

#
torch.backends.cudnn.benchmark = True

# loader = data.Data(cfg)
ckpt = utility.checkpoint(cfg)
loader = data_v2.ImageDataManager(cfg)
model = make_model(cfg, ckpt)
optimzer = make_optimizer(cfg, model)
loss = make_loss(cfg, ckpt) if not args.test_only else None

start = -1
if cfg.load != '':
    start, model, optimizer = ckpt.resume_from_checkpoint(
        osp.join(ckpt.dir, 'model-latest.pth'), model, optimzer)
    start = start - 1
if cfg.pre_train != '':
    ckpt.load_pretrained_weights(model, cfg.pre_train)

scheduler = make_scheduler(cfg, optimzer, start)

# print('[INFO] System infomation: \n {}'.format(get_pretty_env_info()))
ckpt.write_log('[INFO] Model parameters: {com[0]} flops: {com[1]}'.format(com=compute_model_complexity(model, (1, 3, cfg.height, cfg.width))
                                                                          ))

engine = engine_v3.Engine(cfg, model, optimzer,
                          scheduler, loss, loader, ckpt)
# engine = engine.Engine(args, model, loss, loader, ckpt)

n = start + 1
while not engine.terminate():

    n += 1
    engine.train()
    if cfg.test_every != 0 and n % cfg.test_every == 0:
        engine.test()
    elif n == cfg.epochs:
        engine.test()
