from graph.workflow import build_workflow


def main():

    print("=" * 60)
    print("          DEVOPS MULTI-AGENT WORKFLOW")
    print("=" * 60)

    print("\nBuilding LangGraph workflow...")

    workflow = build_workflow()

    print("Workflow created successfully.")

    initial_state = {
        "messages": []
    }

    print("\nStarting workflow...")
    print("-" * 60)

    final_state = workflow.invoke(initial_state)

    print("-" * 60)
    print("\nWORKFLOW COMPLETED")
    print("=" * 60)

    print("\nFinal State:")

    for key, value in final_state.items():
        print(f"\n{key}: {value}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()