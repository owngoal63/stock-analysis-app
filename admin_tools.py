import sqlite3
import os
from pathlib import Path
import logging
from datetime import datetime

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'user_deletion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def delete_users(db_path: str = "./data/auth.db", admin_password: str = None, backup: bool = True):
    """
    Administrative tool to delete users from the database
    
    Args:
        db_path: Path to the SQLite database
        admin_password: Administrative password for confirmation
        backup: Whether to create a backup before deletion
    """
    logger = setup_logging()
    
    try:
        # Verify database exists
        if not os.path.exists(db_path):
            logger.error(f"Database not found at {db_path}")
            return False
            
        # Create backup if requested
        if backup:
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Creating backup at {backup_path}")
            import shutil
            shutil.copy2(db_path, backup_path)
            
        # Get administrator password
        # if admin_password is None:
        #     admin_password = input("Enter administrator password for confirmation: ")
            
        # Double-check with administrator
        confirmation = input("""
WARNING: This will delete ALL users from the database.
This action cannot be undone (except by restoring from backup).
Type 'DELETE ALL USERS' to confirm: """)
        
        if confirmation != "DELETE ALL USERS":
            logger.warning("Operation cancelled - confirmation phrase did not match")
            return False
            
        # Connect to database and delete users
        conn = sqlite3.connect(db_path)
        try:
            # First get count of users
            cursor = conn.cursor()
            user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            
            logger.info(f"Found {user_count} users in database")
            
            # Delete all users
            cursor.execute("DELETE FROM users")
            
            # Log the number of deleted rows
            deleted_count = cursor.rowcount
            
            # Commit the deletion
            conn.commit()
            
            logger.info(f"Deleted {deleted_count} users from database")
            
            # Close connection after commit
            conn.close()
            
            # Create new connection for VACUUM
            vacuum_conn = sqlite3.connect(db_path)
            vacuum_conn.execute("VACUUM")
            vacuum_conn.close()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
            
        logger.info("User deletion completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during user deletion: {str(e)}")
        return False

if __name__ == "__main__":
    # Get database path
    db_path = input("Enter database path [./data/auth.db]: ").strip() or "./data/auth.db"
    
    # Ask about backup
    backup = input("Create backup before deletion? [Y/n]: ").strip().lower() != 'n'
    
    # Run deletion
    success = delete_users(db_path=db_path, backup=backup)
    
    if success:
        print("User deletion completed successfully. Check the log file for details.")
    else:
        print("User deletion failed. Check the log file for details.")