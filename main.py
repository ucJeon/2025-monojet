import os
import importlib
import inspect

INTERFACE_DIR = "interface"

def load_interfaces():
    modules = []
    for f in os.listdir(INTERFACE_DIR):
        if f.endswith(".py") and not f.startswith("__"):
            name = f[:-3]
            module = importlib.import_module(f"{INTERFACE_DIR}.{name}")
            modules.append(module)
    return modules


def main():
    tasks = load_interfaces()

    if not tasks:
        print("No tasks found.")
        return

    print("Choose the tasks\n")
    for i, module in enumerate(tasks, 1):
        print(f"{i}. {module.name} - {module.description}")

    try:
        choice = int(input("\nEnter number: "))
        if choice < 1 or choice > len(tasks):
            raise ValueError
    except:
        print("Invalid choice")
        return

    selected_module = tasks[choice - 1]

    # 🔥 keyword 입력
    keyword = input("Enter keyword (function name): ").strip()

    # 함수 존재 여부 확인
    if not hasattr(selected_module, keyword):
        print("Function not found. Exit.")
        return

    func = getattr(selected_module, keyword)

    # 함수인지 확인
    if not callable(func):
        print("Not a callable function. Exit.")
        return

    # 🔥 파라미터 처리
    params = []

    # introspection으로 함수 파라미터 확인
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        value = input(f"Enter value for {param.name}: ")
        params.append(value)

    # 🔥 실행
    func(*params)

    # 🔥 {함수이름}_params 변수 출력
    param_var_name = f"{keyword}_params"

    if hasattr(selected_module, param_var_name):
        param_info = getattr(selected_module, param_var_name)
        if param_info is not None:
            print("\nDefined parameter info:")
            print(param_info)


if __name__ == "__main__":
    main()

