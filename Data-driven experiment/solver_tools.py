import numpy as np
import torch
import tedeous
from tedeous.callbacks import early_stopping, plot
from tedeous.data import Domain, Conditions, Equation
from tedeous.device import check_device
from tedeous.model import Model
from tedeous.models import mat_model
from tedeous.optimizers.optimizer import Optimizer


def get_grid_for_solver(arg0) -> torch.Tensor:
    """
    Prepares the input data for the solver by converting a list of coordinates into a torch tensor.

    Args:
        arg0: The input coordinate list.

    Returns:
        torch.Tensor: A torch tensor reshaped for the solver input.
    """
    coord_list_train = [arg0]
    coord_list_train = torch.tensor(coord_list_train)
    return coord_list_train.reshape(-1, 1).float()


def set_boundary(arg_values: list, func_values: list, variable_names: [str] = 'y') -> tedeous.data.Conditions:
    """
    Sets the boundary conditions for the solver based on the provided argument and function values.

    Args:
        arg_values (list): List of argument values.
        func_values (list): List of function values corresponding to the arguments.
        variable_names (list of str): Names of the variables for which boundaries are set.

    Returns:
        tedeous.data.Conditions: The boundary conditions object.
    """
    boundaries = Conditions()
    for (arg_val, func_val, var_name) in zip(arg_values, func_values, variable_names):
        boundaries.dirichlet({var_name: arg_val}, value=func_val)  # setting initial cond
    return boundaries


def get_nn() -> torch.nn.Sequential:
    """
    Creates and returns a neural network model with a specific architecture.

    Returns:
        torch.nn.Sequential: A neural network model with the defined architecture.
    """

    return torch.nn.Sequential(
        torch.nn.Linear(1, 100),
        torch.nn.Tanh(),
        torch.nn.Linear(100, 100),
        torch.nn.Tanh(),
        torch.nn.Linear(100, 100),
        torch.nn.Tanh(),
        torch.nn.Linear(100, 1),
    )


def get_solution(eq, poynting_vec: np.ndarray, grid_training: np.ndarray,
                 grid_test: np.ndarray, img_dir: str, training_epochs: int = 10000,
                 mode: str = 'autograd') -> (torch.Tensor, torch.Tensor):
    """
    Solve the given equation using the specified solver mode and return the predicted solutions for training and
    testing grids.

    Args:
        eq: The equation to solve.
        poynting_vec: The Poynting vector data.
        grid_training: The training grid data.
        grid_test: The testing grid data.
        img_dir: The directory to save solution images.
        training_epochs: Number of epochs for training (default is 10000).
        mode: The solver mode to use (default is 'autograd').

    Returns:
        tuple: Predicted solutions for the training and testing grids.
    """

    grid_training = get_grid_for_solver(grid_training)
    grid_test = get_grid_for_solver(grid_test)

    domain = Domain()  # Domain class for domain initialization
    domain.variable('y', grid_training, None)

    boundaries = set_boundary([0.0], [-1])

    equation = Equation()
    equation.add(eq)

    net = get_nn() if mode in {'NN', 'autograd'} else mat_model(domain, equation)

    model = Model(net, domain, equation, boundaries)
    model.compile(mode, lambda_operator=1, lambda_bound=40)
    cb_es = early_stopping.EarlyStopping(eps=1e-6,
                                         loss_window=100,
                                         no_improvement_patience=1000,
                                         patience=3,
                                         randomize_parameter=1e-5,
                                         info_string_every=1000)
    cb_plots = plot.Plots(save_every=1000, print_every=None, img_dir=img_dir)
    optimizer = Optimizer('Adam', {'lr': 1e-3})
    model.train(optimizer, training_epochs, save_model=False, callbacks=[cb_es, cb_plots])
    predicted_solution_training = check_device(net(grid_training)).reshape(-1)
    predicted_solution_test = check_device(net(grid_test)).reshape(-1)
    return predicted_solution_training, predicted_solution_test
