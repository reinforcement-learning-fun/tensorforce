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
from __future__ import print_function
from __future__ import division

from tensorforce import TensorForceError
from tensorforce.agents import BatchAgent
from tensorforce.models import PGProbRatioModel


class TRPOAgent(BatchAgent):
    """
    Trust Region Policy Optimization ([Schulman et al., 2015](https://arxiv.org/abs/1502.05477)) agent.
    """

    def __init__(
        self,
        states_spec,
        actions_spec,
        network_spec,
        device=None,
        session_config=None,
        scope='trpo',
        saver_spec=None,
        summary_spec=None,
        distributed_spec=None,
        discount=0.99,
        normalize_rewards=False,
        variable_noise=None,
        distributions_spec=None,
        entropy_regularization=None,
        baseline_mode=None,
        baseline=None,
        baseline_optimizer=None,
        gae_lambda=None,
        preprocessing=None,
        exploration=None,
        reward_preprocessing=None,
        batched_observe=1000,
        batch_size=1000,
        keep_last_timestep=True,
        likelihood_ratio_clipping=None,
        learning_rate=1e-3,
        cg_max_iterations=20,
        cg_damping=1e-3,
        cg_unroll_loop=False
    ):
        """
        Creates a Trust Region Policy Optimization ([Schulman et al., 2015](https://arxiv.org/abs/1502.05477)) agent.

        Args:
            states_spec: Dict containing at least one state definition. In the case of a single state,
               keys `shape` and `type` are necessary. For multiple states, pass a dict of dicts where each state
               is a dict itself with a unique name as its key.
            actions_spec: Dict containing at least one action definition. Actions have types and either `num_actions`
                for discrete actions or a `shape` for continuous actions. Consult documentation and tests for more.
            network_spec: List of layers specifying a neural network via layer types, sizes and optional arguments
                such as activation or regularisation. Full examples are in the examples/configs folder.
            device: Device string specifying model device.
            session_config: optional tf.ConfigProto with additional desired session configurations
            scope: TensorFlow scope, defaults to agent name (e.g. `dqn`).
            saver_spec: Dict specifying automated saving. Use `directory` to specify where checkpoints are saved. Use
                either `seconds` or `steps` to specify how often the model should be saved. The `load` flag specifies
                if a model is initially loaded (set to True) from a file `file`.
            summary_spec: Dict specifying summaries for TensorBoard. Requires a 'directory' to store summaries, `steps`
                or `seconds` to specify how often to save summaries, and a list of `labels` to indicate which values
                to export, e.g. `losses`, `variables`. Consult neural network class and model for all available labels.
            distributed_spec: Dict specifying distributed functionality. Use `parameter_server` and `replica_model`
                Boolean flags to indicate workers and parameter servers. Use a `cluster_spec` key to pass a TensorFlow
                cluster spec.
            discount: Float specifying reward discount factor.
            normalize_rewards: Boolean flag specifying whether to normalize rewards, default False.
            variable_noise: Experimental optional parameter specifying variable noise (NoisyNet).
            distributions_spec: Optional dict specifying action distributions to override default distribution choices.
                Must match action names.
            entropy_regularization: Optional positive float specifying an entropy regularization value.
            baseline_mode: String specifying baseline mode, `states` for a separate baseline per state, `network`
                for sharing parameters with the training network.
            baseline: Optional dict specifying baseline type (e.g. `mlp`, `cnn`), and its layer sizes. Consult
             examples/configs for full example configurations.
            baseline_optimizer: Optional dict specifying an optimizer and its parameters for the baseline
                following the same conventions as the main optimizer.
            gae_lambda: Optional float specifying lambda parameter for generalized advantage estimation.
            preprocessing: Optional list of preprocessors (e.g. `image_resize`, `grayscale`) to apply to state. Each
                preprocessor is a dict containing a type and optional necessary arguments.
            exploration: Optional dict specifying exploration type (epsilon greedy strategies or Gaussian noise)
                and arguments.
            reward_preprocessing: Optional dict specifying reward preprocessor using same syntax as state preprocessing.
            batched_observe: Optional int specifying how many observe calls are batched into one session run.
                Without batching, throughput will be lower because every `observe` triggers a session invocation to
                update rewards in the graph.
            batch_size: Int specifying number of samples collected via `observe` before an update is executed.
            keep_last_timestep: Boolean flag specifying whether last sample is kept, default True.
            likelihood_ratio_clipping: Optional clipping of likelihood ratio between old and new policy.
            learning_rate: Learning rate which may be interpreted differently according to optimizer, e.g. a natural
                gradient optimizer interprets the learning rate as the max kl-divergence between old and updated policy.
            cg_max_iterations: Int > 0 specifying conjugate gradient iterations, typically 10-20 are sufficient to
                find effective approximate solutions.
            cg_damping: Conjugate gradient damping value to increase numerical stability.
            cg_unroll_loop: Boolean indicating whether loop unrolling in TensorFlow is to be used which seems to
                impact performance negatively at this point, default False.
        """
        if network_spec is None:
            raise TensorForceError("No network_spec provided.")

        self.optimizer = dict(
            type='optimized_step',
            optimizer=dict(
                type='natural_gradient',
                learning_rate=learning_rate,
                cg_max_iterations=cg_max_iterations,
                cg_damping=cg_damping,
                cg_unroll_loop=cg_unroll_loop,
            ),
            ls_max_iterations=10,
            ls_accept_ratio=0.9,
            ls_mode='exponential',
            ls_parameter=0.5,
            ls_unroll_loop=False
        )

        self.network_spec = network_spec
        self.device = device
        self.session_config = session_config
        self.scope = scope
        self.saver_spec = saver_spec
        self.summary_spec = summary_spec
        self.distributed_spec = distributed_spec
        self.discount = discount
        self.normalize_rewards = normalize_rewards
        self.variable_noise = variable_noise
        self.preprocessing = preprocessing
        self.exploration = exploration
        self.reward_preprocessing = reward_preprocessing
        self.distributions_spec = distributions_spec
        self.entropy_regularization = entropy_regularization
        self.baseline_mode = baseline_mode
        self.baseline = baseline
        self.baseline_optimizer = baseline_optimizer
        self.gae_lambda = gae_lambda
        self.likelihood_ratio_clipping = likelihood_ratio_clipping

        super(TRPOAgent, self).__init__(
            states_spec=states_spec,
            actions_spec=actions_spec,
            preprocessing=preprocessing,
            exploration=exploration,
            batched_observe=batched_observe,
            batch_size=batch_size,
            keep_last_timestep=keep_last_timestep
        )

    def initialize_model(self):
        return PGProbRatioModel(
            states_spec=self.states_spec,
            actions_spec=self.actions_spec,
            network_spec=self.network_spec,
            device=self.device,
            session_config=self.session_config,
            scope=self.scope,
            saver_spec=self.saver_spec,
            summary_spec=self.summary_spec,
            distributed_spec=self.distributed_spec,
            optimizer=self.optimizer,
            discount=self.discount,
            normalize_rewards=self.normalize_rewards,
            variable_noise=self.variable_noise,
            preprocessing=self.preprocessing,
            exploration=self.exploration,
            reward_preprocessing=self.reward_preprocessing,
            distributions_spec=self.distributions_spec,
            entropy_regularization=self.entropy_regularization,
            baseline_mode=self.baseline_mode,
            baseline=self.baseline,
            baseline_optimizer=self.baseline_optimizer,
            gae_lambda=self.gae_lambda,
            likelihood_ratio_clipping=self.likelihood_ratio_clipping
        )
