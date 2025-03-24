import os
import sys
import json
import argparse
from typing import List, Optional

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("MSSkillsUpdater")

def get_current_skills() -> List[str]:
    """
    Get the current list of Microsoft Applied Skills from the state file.
    
    Returns:
        List[str]: List of skill names
    """
    project_root = get_project_root()
    state_file = os.path.join(project_root, "data/watchers/ms_applied_skills/state.json")
    
    if not os.path.exists(state_file):
        logger.warning(f"State file not found: {state_file}")
        return []
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        skills = state.get("last_value", {}).get("skills", [])
        logger.info(f"Loaded {len(skills)} skills from state file")
        return skills
    except Exception as e:
        logger.error(f"Error loading skills from state file: {str(e)}")
        return []

def update_skills_in_watcher(skills: List[str]):
    """
    Update the KNOWN_SKILLS list in the ms_skills_watcher.py file.
    
    Args:
        skills (List[str]): Updated list of skills
    """
    try:
        project_root = get_project_root()
        watcher_file = os.path.join(project_root, "src/watchers/ms_skills_watcher.py")
        
        with open(watcher_file, 'r') as f:
            content = f.read()
        
        # Find the KNOWN_SKILLS list
        start_marker = "KNOWN_SKILLS = ["
        end_marker = "    ]"
        
        start_index = content.find(start_marker)
        if start_index == -1:
            logger.error("Could not find KNOWN_SKILLS list in the watcher file")
            return
        
        start_index += len(start_marker)
        end_index = content.find(end_marker, start_index)
        if end_index == -1:
            logger.error("Could not find end of KNOWN_SKILLS list in the watcher file")
            return
        
        # Create new skills list content
        skills_content = "\n"
        for skill in skills:
            skills_content += f'        "{skill}",\n'
        
        # Replace the list content
        new_content = content[:start_index] + skills_content + content[end_index:]
        
        # Write back to the file
        with open(watcher_file, 'w') as f:
            f.write(new_content)
        
        logger.info(f"Updated KNOWN_SKILLS list in {watcher_file} with {len(skills)} skills")
    except Exception as e:
        logger.error(f"Error updating watcher file: {str(e)}")

def update_state_file(skills: List[str], count: Optional[int] = None):
    """
    Update the state file with the new skills list.
    
    Args:
        skills (List[str]): Updated list of skills
        count (int, optional): Override the count value (default: len(skills))
    """
    try:
        project_root = get_project_root()
        state_file = os.path.join(project_root, "data/watchers/ms_applied_skills/state.json")
        
        if not os.path.exists(state_file):
            logger.warning(f"State file not found: {state_file}")
            return
        
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # Update the skills list
        if "last_value" in state:
            state["last_value"]["skills"] = skills
            state["last_value"]["count"] = count if count is not None else len(skills)
        
        # Write back to the file
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Updated state file with {len(skills)} skills")
    except Exception as e:
        logger.error(f"Error updating state file: {str(e)}")

def add_skills(new_skills: List[str], update_state: bool = True):
    """
    Add new skills to the list.
    
    Args:
        new_skills (List[str]): New skills to add
        update_state (bool): Whether to update the state file
    """
    current_skills = get_current_skills()
    updated_skills = list(current_skills)
    
    # Add new skills that don't already exist
    added_skills = []
    for skill in new_skills:
        if skill not in updated_skills:
            updated_skills.append(skill)
            added_skills.append(skill)
    
    if not added_skills:
        logger.info("No new skills to add")
        return
    
    logger.info(f"Adding {len(added_skills)} new skills: {', '.join(added_skills)}")
    
    # Update the watcher file
    update_skills_in_watcher(updated_skills)
    
    # Update the state file if requested
    if update_state:
        update_state_file(updated_skills)

def remove_skills(skills_to_remove: List[str], update_state: bool = True):
    """
    Remove skills from the list.
    
    Args:
        skills_to_remove (List[str]): Skills to remove
        update_state (bool): Whether to update the state file
    """
    current_skills = get_current_skills()
    updated_skills = [skill for skill in current_skills if skill not in skills_to_remove]
    
    removed_skills = [skill for skill in skills_to_remove if skill in current_skills]
    
    if not removed_skills:
        logger.info("No skills to remove")
        return
    
    logger.info(f"Removing {len(removed_skills)} skills: {', '.join(removed_skills)}")
    
    # Update the watcher file
    update_skills_in_watcher(updated_skills)
    
    # Update the state file if requested
    if update_state:
        update_state_file(updated_skills)

def main():
    """Main function to parse arguments and update skills."""
    parser = argparse.ArgumentParser(description="Update Microsoft Applied Skills list")
    
    # Create a mutually exclusive group for the action
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--list",
        action="store_true",
        help="List current skills",
    )
    action_group.add_argument(
        "--add",
        nargs="+",
        help="Add new skills (provide one or more skill names)",
    )
    action_group.add_argument(
        "--remove",
        nargs="+",
        help="Remove skills (provide one or more skill names)",
    )
    action_group.add_argument(
        "--count",
        type=int,
        help="Update the count value in the state file",
    )
    
    parser.add_argument(
        "--no-state-update",
        action="store_true",
        help="Don't update the state file (only update the watcher code)",
    )
    
    args = parser.parse_args()
    
    # List current skills
    if args.list:
        skills = get_current_skills()
        print("\nCurrent Microsoft Applied Skills:")
        for i, skill in enumerate(skills, 1):
            print(f"{i}. {skill}")
        print(f"\nTotal: {len(skills)} skills")
        return
    
    # Add new skills
    if args.add:
        add_skills(args.add, not args.no_state_update)
    
    # Remove skills
    if args.remove:
        remove_skills(args.remove, not args.no_state_update)
    
    # Update count
    if args.count is not None:
        skills = get_current_skills()
        update_state_file(skills, args.count)
        logger.info(f"Updated count to {args.count}")

if __name__ == "__main__":
    main() 