import numpy as np
from collections import deque

class DynamicDifficulty:
    """
    Class to handle dynamic difficulty adjustment using reinforcement learning techniques.
    This class implements a simple Q-learning approach to determine when to adjust difficulty.
    """
    
    def __init__(self, initial_difficulty="Easy", learning_rate=0.1, discount_factor=0.9, exploration_rate=0.2):
        self.difficulties = ["Easy", "Medium", "Hard"]
        self.current_difficulty = initial_difficulty
        self.learning_rate = learning_rate  # Alpha
        self.discount_factor = discount_factor  # Gamma
        self.exploration_rate = exploration_rate  # Epsilon
        
        # Q-table: state (difficulty + performance) -> action (keep, increase, decrease)
        self.q_table = {}
        
        # Keep track of recent scores for performance evaluation
        self.recent_scores = deque(maxlen=3)
        
        # Initialize the Q-table with default values
        self._initialize_q_table()
    
    def _initialize_q_table(self):
        """Initialize Q-table with zeros for all state-action pairs"""
        # States: each difficulty + performance level (low, medium, high)
        performance_levels = ["low", "medium", "high"]
        
        for difficulty in self.difficulties:
            for performance in performance_levels:
                state = f"{difficulty}_{performance}"
                self.q_table[state] = {
                    "keep": 0.0,
                    "increase": 0.0,
                    "decrease": 0.0
                }
    
    def _get_performance_level(self, score):
        """Convert numeric score to performance level"""
        if score < 4.0:
            return "low"
        elif score < 7.0:
            return "medium"
        else:
            return "high"
    
    def _get_current_state(self):
        """Get the current state based on difficulty and recent performance"""
        if not self.recent_scores:
            # Default to medium performance if no scores yet
            return f"{self.current_difficulty}_medium"
        
        avg_score = sum(self.recent_scores) / len(self.recent_scores)
        performance = self._get_performance_level(avg_score)
        return f"{self.current_difficulty}_{performance}"
    
    def _get_valid_actions(self):
        """Get valid actions based on current difficulty"""
        if self.current_difficulty == "Easy":
            return ["keep", "increase"]
        elif self.current_difficulty == "Hard":
            return ["keep", "decrease"]
        else:  # Medium
            return ["keep", "increase", "decrease"]
    
    def _choose_action(self, state):
        """Choose action using epsilon-greedy strategy"""
        valid_actions = self._get_valid_actions()
        
        # Explore: random action
        if np.random.random() < self.exploration_rate:
            return np.random.choice(valid_actions)
        
        # Exploit: best action based on Q-values
        q_values = {action: self.q_table[state][action] for action in valid_actions}
        max_q = max(q_values.values())
        best_actions = [action for action, q_val in q_values.items() if q_val == max_q]
        
        return np.random.choice(best_actions)
    
    def _apply_action(self, action):
        """Apply the selected action to change difficulty"""
        if action == "keep":
            return self.current_difficulty
        
        current_idx = self.difficulties.index(self.current_difficulty)
        
        if action == "increase" and current_idx < len(self.difficulties) - 1:
            return self.difficulties[current_idx + 1]
        elif action == "decrease" and current_idx > 0:
            return self.difficulties[current_idx - 1]
        
        # If action is invalid, keep current difficulty
        return self.current_difficulty
    
    def _get_reward(self, old_state, new_state, score):
        """
        Calculate reward for the taken action
        Reward is higher if:
        - User performs well at increased difficulty
        - User improves performance at the same difficulty
        - User performs better after difficulty decrease
        """
        old_diff, old_perf = old_state.split('_')
        new_diff, new_perf = new_state.split('_')
        
        # Base reward
        reward = 0
        
        # Reward for appropriate difficulty
        perf_scores = {"low": 1, "medium": 2, "high": 3}
        diff_scores = {"Easy": 1, "Medium": 2, "Hard": 3}
        
        perf_level = perf_scores[new_perf]
        diff_level = diff_scores[new_diff]
        
        # Ideal match: performance level matches difficulty level
        match_quality = 1 - abs(perf_level - diff_level) / 2
        reward += 5 * match_quality
        
        # Additional reward for improvement
        if perf_scores[new_perf] > perf_scores[old_perf]:
            reward += 3
        
        return reward
    
    def add_score(self, score):
        """Add a new score and update the learning model"""
        self.recent_scores.append(score)
        
        if len(self.recent_scores) < 2:
            # Need at least 2 scores to learn
            return self.current_difficulty, None
        
        old_state = self._get_current_state()
        action = self._choose_action(old_state)
        new_difficulty = self._apply_action(action)
        
        # If difficulty changed, update Q-values
        if new_difficulty != self.current_difficulty:
            # Simulate new state after action
            temp_difficulty = self.current_difficulty
            self.current_difficulty = new_difficulty
            new_state = self._get_current_state()
            
            # Calculate reward
            reward = self._get_reward(old_state, new_state, score)
            
            # Get max Q-value for the new state
            valid_actions = self._get_valid_actions()
            next_q_values = [self.q_table[new_state][a] for a in valid_actions]
            max_next_q = max(next_q_values) if next_q_values else 0
            
            # Update Q-value using Q-learning formula
            self.q_table[old_state][action] = (1 - self.learning_rate) * self.q_table[old_state][action] + \
                                              self.learning_rate * (reward + self.discount_factor * max_next_q)
            
            # Reset for actual state update
            self.current_difficulty = temp_difficulty
            
            explanation = self._get_difficulty_change_explanation(old_state, action, score)
            
            # Actually update the difficulty
            self.current_difficulty = new_difficulty
            return new_difficulty, explanation
        
        return self.current_difficulty, None
    
    def _get_difficulty_change_explanation(self, state, action, score):
        """Generate an explanation for the difficulty change"""
        difficulty, performance = state.split('_')
        
        if action == "increase":
            return (
                f"Based on your recent performance (average score: {sum(self.recent_scores)/len(self.recent_scores):.1f}), "
                f"the system has increased the difficulty to {self.difficulties[self.difficulties.index(difficulty) + 1]}. "
                f"You've demonstrated good understanding of the questions at the {difficulty} level."
            )
        elif action == "decrease":
            return (
                f"To better match your current performance level (average score: {sum(self.recent_scores)/len(self.recent_scores):.1f}), "
                f"the system has decreased the difficulty to {self.difficulties[self.difficulties.index(difficulty) - 1]}. "
                f"This will help you build confidence and improve your answers."
            )
        else:
            return None
    
    def get_current_difficulty(self):
        """Get the current difficulty level"""
        return self.current_difficulty
