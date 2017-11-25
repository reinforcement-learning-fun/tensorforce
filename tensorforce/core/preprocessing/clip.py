# Copyright 2017 reinforce.io. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from tensorforce.core.preprocessing import Preprocessor


class Clip(Preprocessor):
    """
    Clip by min/max.
    """
    def __init__(self, min, max):
        super(Clip, self).__init__()
        self.min = min
        self.max = max

    def process(self, state):
        return tf.clip_by_value(t=state, clip_value_min=self.min, clip_value_max=self.max)
