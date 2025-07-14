# RL Integration Guide for Dynamic Difficulty Adjustment

## Overview
This document explains how the Reinforcement Learning (RL) module for dynamic difficulty adjustment
has been integrated into the Interview Preparation Assistant.

## How It Works
The system uses a Q-learning approach to dynamically adjust the interview difficulty based on 
the candidate's performance. Here's how it works:

1. Each time a candidate answers a question, their score is recorded.
2. After collecting enough scores (at least 2), the RL model evaluates:
   - The current difficulty level
   - The candidate's recent performance (average of last 3 scores)

3. The model then decides whether to:
   - Keep the current difficulty
   - Increase the difficulty
   - Decrease the difficulty

4. If a change is suggested, the candidate is shown a modal with an explanation
   and can choose to accept or reject the change.

## States and Actions
- **States**: Combinations of difficulty level (Easy, Medium, Hard) and performance level (low, medium, high)
- **Actions**: keep, increase, decrease difficulty
- **Rewards**: Higher rewards are given when the difficulty matches the candidate's performance level

## Technical Implementation
- `DynamicDifficulty` class in `RL_module/dynamic_difficulty.py` handles the core RL logic
- The Flask backend integrates this in the `/chat` endpoint
- The React frontend has confirmation dialogs to let the user accept/reject changes

## Customization
To adjust the RL behavior:
- Change the learning rate (alpha): controls how quickly the model adapts
- Modify the discount factor (gamma): balances immediate vs. future rewards
- Adjust the exploration rate (epsilon): controls exploration vs. exploitation balance

## Sample Interactions
1. Candidate performs very well on Easy questions (scores > 7) → System suggests Medium difficulty
2. Candidate struggles on Hard questions (scores < 4) → System suggests Medium difficulty
3. Candidate performs consistently at their current level → System maintains current difficulty
