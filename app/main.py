from mermaid.vis import display_graph

def main():
    print("Hello from sql-ag-v2!")
    flag = display_graph()
    if flag:
        print("Done")
    else:
        print("Failed")

if __name__ == "__main__":
    main()
