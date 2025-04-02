from mermaid.vis import display_graph
from workflow.flow import graph

def main():
    print("Hello from sql-ag-v2!")
    question = "List all employee names and their office state location"
    try:
        for event in graph.stream(
        {"question": question}#, config={"recursion_limit": 5}#, "callbacks": [langfuse_handler]}
        ):
            print(event)
            print("\n\n")    
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
