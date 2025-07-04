import json
import os
import re

from utils.file_system import get_project_root


def clean_course_title(title):
    """Clean up course titles by removing prefixes and extracting proper title."""
    clean_title = title

    # Remove common prefixes
    for prefix in ["Course", "Specialization", "Certificate"]:
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):].strip()

    # If title contains "DeepLearning.AI" at the end, split there
    if "DeepLearning.AI" in clean_title:
        parts = clean_title.split("DeepLearning.AI")
        clean_title = parts[0].strip()

    # If title contains "Stanford Online" at the end, split there
    if "Stanford Online" in clean_title:
        parts = clean_title.split("Stanford Online")
        clean_title = parts[0].strip()

    # Look for common patterns where title and description are concatenated
    # Pattern 1: "TitleDescription that starts with a verb"
    # Pattern 2: "TitleGet an overview", "TitleLearn about", etc.
    description_starters = [
        "Learn", "Build", "Design", "Get an", "Examine", "Understand", "Master",
        "Develop", "Explore", "Discover", "Create", "Implement", "Apply"
    ]

    for starter in description_starters:
        # Look for the pattern where title directly connects to description
        pattern = rf"(.+?)({starter}\s.+)"
        match = re.search(pattern, clean_title, re.IGNORECASE)
        if match:
            potential_title = match.group(1).strip()
            potential_desc = match.group(2).strip()

            # Validate the title is reasonable length and doesn't end weirdly
            if 10 <= len(potential_title) <= 80 and len(potential_desc) > 20:
                return potential_title, potential_desc

    # If still too long, try to split on common course name patterns
    if len(clean_title) > 80:
        # Look for uppercase words that might be start of description
        words = clean_title.split()
        for i, word in enumerate(words):
            if i > 2 and word[0].isupper() and word.lower() in ["learn", "build", "design", "get", "examine"]:
                potential_title = " ".join(words[:i]).strip()
                potential_desc = " ".join(words[i:]).strip()
                if 10 <= len(potential_title) <= 80:
                    return potential_title, potential_desc

    return clean_title, None

def clean_deeplearningai_courses():
    """Clean the DeepLearning.AI courses data."""
    project_root = get_project_root()
    courses_file = os.path.join(project_root, "data/deeplearningai/deeplearningai_courses.json")

    if not os.path.exists(courses_file):
        print("DeepLearning.AI courses file not found.")
        return

    # Load existing data
    with open(courses_file, encoding="utf-8") as f:
        courses = json.load(f)

    print(f"Cleaning {len(courses)} courses...")

    # Clean each course
    for course in courses:
        if "title" in course:
            original_title = course["title"]
            cleaned_title, extracted_desc = clean_course_title(original_title)

            course["title"] = cleaned_title

            # If we extracted a description, use it (even if one exists, the extracted one is likely better)
            if extracted_desc:
                course["description"] = extracted_desc

            print(f"Original: {original_title[:80]}...")
            print(f"Cleaned:  {cleaned_title}")
            print(f"Desc:     {course.get('description', 'N/A')[:80]}...")
            print("-" * 50)

    # Save cleaned data
    with open(courses_file, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)

    print(f"Cleaned and saved {len(courses)} courses to {courses_file}")

if __name__ == "__main__":
    clean_deeplearningai_courses()
