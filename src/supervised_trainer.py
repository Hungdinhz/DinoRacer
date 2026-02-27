"""
Supervised Trainer - Train AI từ dữ liệu đã thu thập
Sử dụng Neural Network để học từ hành động của người chơi
"""
import numpy as np
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
import pickle

# Try to import from database
try:
    from src.database_handler import get_connection, get_training_data_count
    DATABASE_AVAILABLE = True
except:
    DATABASE_AVAILABLE = False


def get_data_path():
    """Lấy đường dẫn file training data"""
    return os.path.join(os.path.dirname(__file__), '..', 'training_data.json')


def load_training_data():
    """Load dữ liệu training từ database hoặc file"""
    X = []
    y_jump = []
    y_duck = []
    
    # Thử load từ database trước
    if DATABASE_AVAILABLE:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT distance_to_obstacle, obstacle_type, game_speed, 
                       dino_height, is_jumping, is_ducking,
                       action_jump, action_duck
                FROM training_data
                WHERE quality_score >= 0.7
            """)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            for row in rows:
                X.append([
                    row[0], row[1], row[2], row[3], row[4], row[5]
                ])
                y_jump.append(row[6])
                y_duck.append(row[7])
            
            print(f"Loaded {len(X)} samples from database")
            return np.array(X), np.array(y_jump), np.array(y_duck)
        except Exception as e:
            print(f"Database error: {e}")
    
    # Fallback: load từ file JSON
    try:
        with open(get_data_path(), 'r') as f:
            data = json.load(f)
        
        for sample in data:
            X.append(sample['inputs'])
            y_jump.append(sample['outputs']['jump'])
            y_duck.append(sample['outputs']['duck'])
        
        print(f"Loaded {len(X)} samples from file")
        return np.array(X), np.array(y_jump), np.array(y_duck)
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None


def train_jump_model(X, y, test_size=0.2):
    """Train model cho action nhảy"""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )
    
    # Scale dữ liệu
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train MLP
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32, 16),
        activation='relu',
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)
    
    print(f"Jump Model - Train: {train_score:.4f}, Test: {test_score:.4f}")
    
    return model, scaler


def train_duck_model(X, y, test_size=0.2):
    """Train model cho action cúi"""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32, 16),
        activation='relu',
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1
    )
    
    model.fit(X_train_scaled, y_train)
    
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)
    
    print(f"Duck Model - Train: {train_score:.4f}, Test: {test_score:.4f}")
    
    return model, scaler


def save_models(jump_model, jump_scaler, duck_model, duck_scaler):
    """Lưu models vào file"""
    models_dir = os.path.join(os.path.dirname(__file__), '..')
    
    with open(os.path.join(models_dir, 'jump_model.pkl'), 'wb') as f:
        pickle.dump({'model': jump_model, 'scaler': jump_scaler}, f)
    
    with open(os.path.join(models_dir, 'duck_model.pkl'), 'wb') as f:
        pickle.dump({'model': duck_model, 'scaler': duck_scaler}, f)
    
    print("Models saved successfully!")


def load_models():
    """Load models từ file"""
    models_dir = os.path.join(os.path.dirname(__file__), '..')
    
    try:
        with open(os.path.join(models_dir, 'jump_model.pkl'), 'rb') as f:
            jump_data = pickle.load(f)
        
        with open(os.path.join(models_dir, 'duck_model.pkl'), 'rb') as f:
            duck_data = pickle.load(f)
        
        return jump_data, duck_data
    except:
        return None, None


def predict_action(jump_model, jump_scaler, duck_model, duck_scaler, inputs):
    """
    Dự đoán action từ inputs
    inputs: [distance_to_obstacle, obstacle_type, game_speed, dino_height, is_jumping, is_ducking]
    """
    # Scale inputs
    inputs = np.array(inputs).reshape(1, -1)
    inputs_scaled = jump_scaler.transform(inputs)
    
    # Predict
    jump_prob = jump_model.predict_proba(inputs_scaled)[0][1]
    duck_prob = duck_model.predict_proba(inputs_scaled)[0][1]
    
    # Return action (jump, duck)
    return (1 if jump_prob > 0.5 else 0, 1 if duck_prob > 0.5 else 0, jump_prob, duck_prob)


def train_supervised():
    """Train AI từ dữ liệu đã thu thập"""
    print("=" * 50)
    print("SUPERVISED LEARNING TRAINING")
    print("=" * 50)
    
    # Load data
    print("\nLoading training data...")
    X, y_jump, y_duck = load_training_data()
    
    if X is None or len(X) < 10:
        print("Not enough data to train!")
        return False
    
    print(f"Total samples: {len(X)}")
    print(f"Jump samples: {sum(y_jump)} ({sum(y_jump)/len(y_jump)*100:.1f}%)")
    print(f"Duck samples: {sum(y_duck)} ({sum(y_duck)/len(y_duck)*100:.1f}%)")
    
    # Train jump model
    print("\nTraining Jump Model...")
    jump_model, jump_scaler = train_jump_model(X, y_jump)
    
    # Train duck model
    print("\nTraining Duck Model...")
    duck_model, duck_scaler = train_duck_model(X, y_duck)
    
    # Save models
    print("\nSaving models...")
    save_models(jump_model, jump_scaler, duck_model, duck_scaler)
    
    print("\n" + "=" * 50)
    print("TRAINING COMPLETE!")
    print("=" * 50)
    
    return True


def get_data_stats():
    """Lấy thống kê dữ liệu training"""
    if DATABASE_AVAILABLE:
        try:
            total = get_training_data_count()
            human = get_training_data_count("human")
            ai = get_training_data_count("ai")
            return {"total": total, "human": human, "ai": ai, "source": "database"}
        except:
            pass
    
    # Fallback to file
    try:
        with open(get_data_path(), 'r') as f:
            data = json.load(f)
        
        human = sum(1 for d in data if d.get("source") == "human")
        ai = sum(1 for d in data if d.get("source") == "ai")
        
        return {"total": len(data), "human": human, "ai": ai, "source": "file"}
    except:
        return {"total": 0, "human": 0, "ai": 0}


if __name__ == "__main__":
    # Test training
    train_supervised()
    
    # Test prediction
    print("\nTesting prediction...")
    jump_data, duck_data = load_models()
    
    if jump_data and duck_data:
        # Test với một input mẫu
        test_input = [0.3, 0.0, 0.5, 0.0, 0.0, 0.0]  # Cactus, 30% distance, medium speed
        action = predict_action(
            jump_data['model'], jump_data['scaler'],
            duck_data['model'], duck_data['scaler'],
            test_input
        )
        print(f"Test input: {test_input}")
        print(f"Predicted action: Jump={action[0]}, Duck={action[1]}")
        print(f"Probabilities: Jump={action[2]:.3f}, Duck={action[3]:.3f}")
    else:
        print("No trained models found!")
