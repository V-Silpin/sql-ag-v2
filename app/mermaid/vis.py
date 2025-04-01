from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

from workflow.flow import graph

def display_graph():
    '''
    This function is used to visualize the workflow of the graph
    It will generate a txt file which has the mermaid code.
    Execute it in this site https://mermaid.live/
    '''
    try:
        code = graph.get_graph().draw_mermaid()

        with open("mermaid.txt", "w") as f:
            f.write(code)

        return True
    except Exception as e:

        print(e)    
