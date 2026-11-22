import json
import os
from dataclasses import dataclass

from maya import cmds

from MV_UtilityScripts import maya_utilities


@dataclass(frozen=True)
class BlendShapeTemplate:
    template_name: str
    node_name: str
    target_names: tuple[str, ...]
    # TODO: Add categories and subcategories (head-expression, head-facs, head-arkit,
    # body-customization, body-correction, ...) so the template library can grow.


def get_templates_folder():
    """Returns the folder inside the Maya user folder where templates are saved."""
    user_folder = cmds.internalVar(userAppDir=True)
    return os.path.join(user_folder, "MV_BlendShapeManager", "templates")


def get_shipped_templates_folder():
    """Returns the folder of the example templates that come with the tool. The tool only reads it."""
    tool_folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(tool_folder, "templates")


def get_hidden_templates_file():
    """Returns the file that lists the example templates the user deleted."""
    user_folder = cmds.internalVar(userAppDir=True)
    return os.path.join(user_folder, "MV_BlendShapeManager", "hidden_shipped_templates.json")


def check_template(template):
    """Raises RuntimeError if a name is empty or a target name is used twice."""
    if not template.template_name:
        raise RuntimeError("The template needs a name.")
    if not template.node_name:
        raise RuntimeError("The template needs a blendshape node name.")
    if not template.target_names:
        raise RuntimeError("The template needs at least one target.")

    seen_target_names = []
    for target_name in template.target_names:
        if not target_name:
            raise RuntimeError("Every target needs a name.")
        if target_name in seen_target_names:
            raise RuntimeError(f"The target name '{target_name}' is used more than once.")
        seen_target_names.append(target_name)

    names_to_check = [template.node_name]
    names_to_check.extend(template.target_names)
    for name in names_to_check:
        if not maya_utilities.check_is_valid_maya_name(name):
            raise RuntimeError(
                f"'{name}' is not a valid Maya name. "
                "Use only letters, numbers and _, and do not start with a number."
            )


def write_template_file(template, file_path):
    """Saves the template as a JSON file. Export uses this."""
    check_template(template)
    template_data = {
        "template_name": template.template_name,
        "node_name": template.node_name,
        "target_names": list(template.target_names),
    }
    with open(file_path, "w") as template_file:
        json.dump(template_data, template_file, indent=4)


def read_template_file(file_path):
    """Loads a template from a JSON file. Import uses this."""
    with open(file_path) as template_file:
        try:
            template_data = json.load(template_file)
        except json.JSONDecodeError:
            raise RuntimeError(f"The template file '{file_path}' is broken.")

    try:
        template = BlendShapeTemplate(
            template_name=template_data["template_name"],
            node_name=template_data["node_name"],
            target_names=tuple(template_data["target_names"]),
        )
    except KeyError as error:
        raise RuntimeError(f"The template file '{file_path}' is missing {error}.")

    check_template(template)
    return template


def save_template(template, folder):
    """Saves the template as <template_name>.json. An existing file with that name is replaced."""
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{template.template_name}.json")
    write_template_file(template, file_path)


def list_templates(folder):
    """Returns every template in the folder, sorted by name."""
    # A missing folder only means no template has been saved yet.
    if not os.path.isdir(folder):
        return []

    templates = []
    for file_name in sorted(os.listdir(folder)):
        if file_name.endswith(".json"):
            templates.append(read_template_file(os.path.join(folder, file_name)))
    return templates


def delete_template(template_name, folder):
    file_path = os.path.join(folder, f"{template_name}.json")
    if not os.path.isfile(file_path):
        raise RuntimeError(f"There is no template called '{template_name}'.")
    os.remove(file_path)


def list_shipped_templates(shipped_folder, hidden_file):
    """Returns the example templates, without the ones the user deleted."""
    hidden_names = _read_hidden_template_names(hidden_file)

    templates = []
    for template in list_templates(shipped_folder):
        if template.template_name not in hidden_names:
            templates.append(template)
    return templates


def hide_shipped_template(template_name, hidden_file):
    """Deletes an example template for the user, by hiding it. The file in the tool folder stays."""
    hidden_names = _read_hidden_template_names(hidden_file)
    if template_name not in hidden_names:
        hidden_names.append(template_name)

    os.makedirs(os.path.dirname(hidden_file), exist_ok=True)
    with open(hidden_file, "w") as names_file:
        json.dump(hidden_names, names_file, indent=4)


def _read_hidden_template_names(hidden_file):
    # no file yet just means nothing was hidden so far
    if not os.path.isfile(hidden_file):
        return []

    with open(hidden_file) as names_file:
        try:
            return json.load(names_file)
        except json.JSONDecodeError:
            raise RuntimeError(f"The file '{hidden_file}' is broken.")
