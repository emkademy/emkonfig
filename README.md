# Emkonfig

This is a [Hydra](https://hydra.cc/) alternative for configuration management. It adds features that I found missing in Hydra, and removes some that I found unnecessary.

## Installation

```bash
pip install emkonfig
```

## Usage

### Parse a configuration file

```python
from emkonfig import Emkonfig

emkonfig = Emkonfig("examples/configs/config.yaml")
config = emkonfig.parse()
emkonfig.print(config)
```

As it is in Hydra, the config is a `DictConfig` object coming from [OmegaConf](https://omegaconf.readthedocs.io/en/2.3_branch/).

## Parsers

### Reference YAML parser

You can reference a YAML file path in your configuration, and Emkonfig automatically parses it.

```yaml
# config.yaml
head: ${./path/to/head.yaml}
```

```yaml
# ./path/to/head.yaml
in_features: 512
out_features: 1024
```

Will be parsed as:

```yaml
head:
  in_features: 512
  out_features: 1024
```

### Reference key parser

You can reference a key in your configuration, and Emkonfig automatically parses it.

```yaml
some_parameter: 3.14
some_dict_parameter:
  key1: ${some_parameter}
  key2: some_other_parameter

some_list_parameter:
  - item1
  - ${some_dict_parameter.key2}
  - item3

final_parameter: ${some_list_parameter[2]}
```

Will be parsed as:

```yaml
some_parameter: 3.14
some_dict_parameter:
  key1: 3.14
  key2: some_other_parameter

some_list_parameter:
  - item1
  - some_other_parameter
  - item3

final_parameter: item3
```

### Class slug parser

In Emkonfig, you can register your classes, then reference them using the slug you registered them with. You can either use `emkonfig.registry.register` or `emkonfig.registry.register_class` for this.

```python
# my_project.some_module.some_file.py
from emkonfig.registry import register, register_class

@register("my_class")
class MyClass:
    def __init__(self, a, b=3):
        self.a = a
        self.b = b


class MyOtherClass:
    def __init__(self, c, d):
        self.c = c
        self.d = d

register_class("my_other_class", MyOtherClass, c=2, d=4)
register_class("my_other_class_with_other_params", MyOtherClass, c=3, d=5)
```

Now you can reference these classes in your configuration:

```yaml
_{my_class}:
  a: 1

_{my_class as some_other_name}:
  a: 2
  b: 4

some_key:
  _{my_class as _}:
    a: 3

some_other_key:
  - _{my_other_class}: null

_{my_other_class}: null # to use the default parameters
_{my_other_class_with_other_params}: null
```

Will be parsed as:

```yaml
my_class:
  _target_: my_project.some_module.some_file.MyClass
  a: 1
  b: 3

some_other_name:
  _target_: my_project.some_module.some_file.MyClass
  a: 2
  b: 4

some_key:
  _target_: my_project.some_module.some_file.MyClass
  a: 3
  b: 3

some_other_key:
  - _target_: my_project.some_module.some_file.MyOtherClass
    c: 2
    d: 4

my_other_class:
  _target_: my_project.some_module.some_file.MyOtherClass
  c: 2
  d: 4

my_other_class_with_other_params:
  _target_: my_project.some_module.some_file.MyOtherClass
  c: 3
  d: 5
```

You can directly use these parameters to instantiate these classes:

```python
from emkonfig.utils import instantiate
my_class = instantiate(config.my_class)
```

### Arguments parser

As Hydra, Emkonfig supports arguments parsing. You can pass arguments to your configuration file using `--overwrites`:

```yaml
# config.yaml
some_parameter: 3
some_other_parameter:
  key1: key1
  key2: 3.14
```

```bash
python ./my_project/entrypoint.py --overwrites some_paramter=4 some_other_parameter.key2=2.71
```

The final configuration will be:

```yaml
some_parameter: 4
some_other_parameter:
  key1: key1
  key2: 2.71
```

### Defaults list parser

As it is in Hydra, you can define a list of default values for a key in your configuration. The key refer to the relative directories to your main config file, and the values refer to the `.yaml` files in these directories. Let's say this is the structure of your configs directory

```bash
configs/
  - config.yaml
  - head/
    - linear.yaml
  - backbone/
    - vision_backbone/
      - resnet50.yaml
    - language_backbone/
      - bert.yaml
  - optimizer/
    - adam.yaml
  - callbacks/
    - early_stopping.yaml
    - model_checkpoint.yaml
    - tensorboard.yaml
```

You can reference these yaml files in your `defaults` list as follows:

```yaml
# config.yaml

defaults:
  - head: linear
  - backbone/vision_backbone: resnet50
  - backbone/language_backbone: bert
  - backbone/vision_backbone@model: resnet50 # You can also rename the key using '@'
  - optimizer: adam
  - callbacks:
      - early_stopping
      - model_checkpoint
      - tensorboard
```

Will be parsed as:

```yaml
head: # parsed from configs/head/linear.yaml
backbone:
  vision_backbone: # parsed from configs/backbone/vision_backbone/resnet50.yaml
  language_backbone: # parsed from configs/backbone/language_backbone/bert.yaml
model: # parsed from configs/backbone/vision_backbone/resnet50.yaml
optimizer: # parsed from configs/optimizer/adam.yaml
callbacks:
  -  # parsed from configs/callbacks/early_stopping.yaml
  -  # parsed from configs/callbacks/model_checkpoint.yaml
  -  # parsed from configs/callbacks/tensorboard.yaml
```

### Examples

If you want to see an example configuration file, you can check the `examples/configs/config.yaml` file, and run:

```bash
python ./examples/example.py
```
