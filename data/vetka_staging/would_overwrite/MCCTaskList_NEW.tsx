import React from 'react';
import { useStore } from '../../store/useStore';
import type { Task } from '../../types/task';

// MARKER_MCC_COMPONENT_START
const MCCTaskList: React.FC = () => {
  const { tasks, toggleTask, removeTask } = useStore((state) => ({
    tasks: state.tasks,
    toggleTask: state.toggleTask,
    removeTask: state.removeTask,
  }));

  const handleToggle = (id: string) => {
    toggleTask(id);
  };

  const handleRemove = (id: string) => {
    removeTask(id);
  };

  return (
    <div className="mcc-task-list" style={styles.container}>
      <h2 style={styles.header}>Mission Critical Tasks</h2>
      {tasks.length === 0 ? (
        <div style={styles.emptyState}>
          <p style={styles.emptyText}>No tasks available</p>
        </div>
      ) : (
        <ul style={styles.list}>
          {tasks.map((task) => (
            <TaskItem 
              key={task.id} 
              task={task} 
              onToggle={handleToggle}
              onRemove={handleRemove}
            />
          ))}
        </ul>
      )}
    </div>
  );
};
// MARKER_MCC_COMPONENT_END

// MARKER_TASK_ITEM_START
const TaskItem: React.FC<{
  task: Task;
  onToggle: (id: string) => void;
  onRemove: (id: string) => void;
}> = ({ task, onToggle, onRemove }) => {
  return (
    <li style={styles.taskItem}>
      <div style={styles.taskContent}>
        <input
          type="checkbox"
          checked={task.completed}
          onChange={() => onToggle(task.id)}
          style={styles.checkbox}
        />
        <span 
          style={{
            ...styles.taskText,
            ...(task.completed ? styles.completedTask : {})
          }}
        >
          {task.title}
        </span>
      </div>
      <button 
        onClick={() => onRemove(task.id)}
        style={styles.removeButton}
        aria-label="Remove task"
      >
        ×
      </button>
    </li>
  );
};
// MARKER_TASK_ITEM_END

// MARKER_STYLES_START
const styles = {
  container: {
    backgroundColor: '#0a0a0a',
    border: '1px solid #2a2a2a',
    borderRadius: '4px',
    padding: '16px',
    fontFamily: 'monospace',
    maxWidth: '400px',
  },
  header: {
    color: '#e0e0e0',
    borderBottom: '1px solid #333',
    paddingBottom: '8px',
    marginBottom: '12px',
    fontSize: '18px',
  },
  list: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  taskItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0',
    borderBottom: '1px solid #222',
  },
  taskContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  checkbox: {
    backgroundColor: '#000',
    border: '1px solid #555',
    width: '16px',
    height: '16px',
  },
  taskText: {
    color: '#d0d0d0',
    fontSize: '14px',
  },
  completedTask: {
    textDecoration: 'line-through',
    color: '#777',
  },
  removeButton: {
    backgroundColor: 'transparent',
    border: '1px solid #444',
    color: '#999',
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    cursor: 'pointer',
    fontSize: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyState: {
    textAlign: 'center',
    padding: '20px',
  },
  emptyText: {
    color: '#666',
    fontStyle: 'italic',
  },
};
// MARKER_STYLES_END

export default MCCTaskList;