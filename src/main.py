import asyncio
import argparse
import mapc2022 as mapc2022

from agent.server.agentSchedulerServer import AgentSchedulerServer

async def runClient(host: str, port: int, team: str, password: str, explain: bool) -> None:
    while True:
        try:
            agentScheduler = AgentSchedulerServer(host, port, team, password, explain)
            
            agentScheduler.initialiteStaticValues()
            await agentScheduler.connectAgents()
            agentScheduler.registerAgentsToServers()

            # Run in a loop to handle multiple matches
            while True:
                try:
                    if explain:
                        agentScheduler.explain()

                    await agentScheduler.scheduleAgents()
                    
                # Not the best solution: one error means a match has ended
                except mapc2022.AgentTerminatedError:
                    print("Simulation over")
                    break

        # Not the best solution 2: two error means a simulation has ended
        except mapc2022.AgentTerminatedError:
            print("Contest over")
            break
        
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Agent scheduler for the given team")

    parser.add_argument("--host", dest = "host", metavar = "127.0.0.1", type = str, default = "127.0.0.1",
                    required = False, help = "Server host")
    parser.add_argument("--port", dest = "port", metavar = "12300", type = str, default = "12300",
                    required = False, help = "Server host port")
    parser.add_argument("--team", dest = "team", metavar = "A", type = str, default = "A",
                    required = False, help = "name of the team to be controlled")
    parser.add_argument("--pw", dest = "password", metavar = "1", type = str, default = "1",
                    required = False, help = "team password used for authentication")
    parser.add_argument("--explain", dest = "explain", action="store_true",
                    required = False, help = "show explanation window")
    
    args = parser.parse_args()
    asyncio.run(runClient(args.host, args.port, args.team, args.password, args.explain))        