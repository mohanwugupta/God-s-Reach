"""
Example experiment script for testing the extractor.
"""

# Experiment parameters
rotation_magnitude = 30  # degrees
rotation_direction = "CW"
num_trials = 80
feedback_delay = 100  # milliseconds
cursor_visible = True

# Equipment settings
robot_type = "vbot_planar"
sampling_rate = 1000  # Hz
workspace_width = 40  # cm
workspace_height = 30  # cm

# Participant information
num_subjects = 20
mean_age = 24.5
age_sd = 3.2
handedness = "right-handed"

# Block structure
baseline_trials = 20
adaptation_trials = 40
washout_trials = 20

def setup_experiment():
    """Initialize experiment."""
    print(f"Setting up visuomotor rotation experiment")
    print(f"Rotation: {rotation_magnitude} degrees {rotation_direction}")
    print(f"Total trials: {num_trials}")
    print(f"Participants: {num_subjects}")
    
def run_trial(trial_num):
    """Run a single trial."""
    # Trial logic would go here
    pass

def run_experiment():
    """Main experiment loop."""
    setup_experiment()
    
    for trial in range(num_trials):
        run_trial(trial)
    
    print("Experiment complete!")

if __name__ == "__main__":
    run_experiment()
