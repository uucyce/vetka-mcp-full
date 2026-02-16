// client/src/components/Tasks/TaskList.tsx
const TaskList = () => {
  const { tasks, fetchTasks } = useStore();
  
  useEffect(() => {
    fetchTasks();
    
    // SocketIO listener
    socket.on('task_progress', (data) => {
      // Update UI
    });
  }, []);
};