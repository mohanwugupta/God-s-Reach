"""
Design Space Analysis Module

This module provides tools for analyzing the motor learning design space:
1. Parameter matrix construction from experiments/groups
2. Dimensionality reduction (PCA, t-SNE, UMAP)
3. Clustering analysis (hierarchical, k-means)
4. Visualization functions

Usage:
    from analysis.design_space import DesignSpaceAnalyzer
    
    analyzer = DesignSpaceAnalyzer('out/designspace.db')
    pca_results = analyzer.run_pca(n_components=3)
    analyzer.plot_design_space(pca_results, color_by='perturbation_type')
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import json

# Core scientific computing
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


class DesignSpaceAnalyzer:
    """
    Analyze motor learning design space using dimensionality reduction and clustering.
    
    Supports both experiment-level and group-level analysis.
    """
    
    def __init__(self, db_path: str = None, level: str = 'group'):
        """
        Initialize design space analyzer.
        
        Args:
            db_path: Path to SQLite database (if None, loads from JSON)
            level: 'experiment' or 'group' for analysis unit
        """
        self.db_path = db_path
        self.level = level
        self.experiments = []
        self.groups = []
        self.parameter_matrix = None
        self.feature_names = None
        self.scaler = StandardScaler()
        
        if db_path:
            self.load_from_database(db_path)
        
        logger.info(f"DesignSpaceAnalyzer initialized (level={level})")
    
    def load_from_database(self, db_path: str):
        """Load experiments and groups from database."""
        from database.models import DatabaseConnection, Experiment, Group
        
        db = DatabaseConnection(db_path)
        session = db.get_session()
        
        try:
            # Load experiments
            experiments = session.query(Experiment).all()
            self.experiments = [exp.to_dict() for exp in experiments]
            
            # Load groups if in group mode
            if self.level == 'group':
                groups = session.query(Group).all()
                self.groups = [grp.to_dict() for grp in groups]
                logger.info(f"Loaded {len(self.groups)} groups from database")
            
            logger.info(f"Loaded {len(self.experiments)} experiments from database")
            
        finally:
            session.close()
    
    def load_from_json(self, json_path: str):
        """Load experiments/groups from JSON file (batch processing output)."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            # Check if group-level or experiment-level
            if data and 'groups' in data[0]:
                # Flatten groups from all experiments
                self.groups = []
                for exp_data in data:
                    if 'groups' in exp_data:
                        self.groups.extend(exp_data['groups'])
                logger.info(f"Loaded {len(self.groups)} groups from JSON")
            else:
                self.experiments = data
                logger.info(f"Loaded {len(self.experiments)} experiments from JSON")
    
    def create_parameter_matrix(self, 
                                numerical_params: List[str] = None,
                                categorical_params: List[str] = None,
                                handle_missing: str = 'median') -> pd.DataFrame:
        """
        Create parameter matrix for analysis.
        
        Args:
            numerical_params: List of numerical parameter names
            categorical_params: List of categorical parameter names
            handle_missing: How to handle missing values ('median', 'mean', 'drop', 'zero')
            
        Returns:
            DataFrame with rows=groups/experiments, columns=features
        """
        # Determine data source
        data_source = self.groups if self.level == 'group' and self.groups else self.experiments
        
        if not data_source:
            raise ValueError("No data loaded. Call load_from_database() or load_from_json() first.")
        
        # Default parameters if not specified
        if numerical_params is None:
            numerical_params = [
                'sample_size_n', 'age_mean', 'age_sd',
                'rotation_magnitude_deg', 'force_field_strength',
                'adaptation_trials', 'baseline_trials', 'washout_trials',
                'cursor_size_mm', 'feedback_delay_ms'
            ]
        
        if categorical_params is None:
            categorical_params = [
                'perturbation_type', 'perturbation_class', 'perturbation_schedule',
                'feedback_type', 'feedback_modality',
                'instruction_awareness', 'effector'
            ]
        
        # Build matrix
        rows = []
        row_ids = []
        
        for item in data_source:
            row = {}
            item_id = item.get('id', item.get('group_id', item.get('experiment_id', f'item_{len(rows)}')))
            
            # Extract numerical parameters
            for param in numerical_params:
                value = self._extract_param_value(item, param)
                if value is not None:
                    row[param] = float(value)
                else:
                    row[param] = np.nan
            
            # Extract categorical parameters (will be one-hot encoded)
            for param in categorical_params:
                value = self._extract_param_value(item, param)
                if value is not None:
                    row[param] = str(value)
                else:
                    row[param] = 'unknown'
            
            rows.append(row)
            row_ids.append(item_id)
        
        # Create DataFrame
        df = pd.DataFrame(rows, index=row_ids)
        
        # Handle missing numerical values
        numerical_cols = [c for c in df.columns if c in numerical_params]
        
        if handle_missing == 'median':
            df[numerical_cols] = df[numerical_cols].fillna(df[numerical_cols].median())
        elif handle_missing == 'mean':
            df[numerical_cols] = df[numerical_cols].fillna(df[numerical_cols].mean())
        elif handle_missing == 'zero':
            df[numerical_cols] = df[numerical_cols].fillna(0)
        elif handle_missing == 'drop':
            df = df.dropna(subset=numerical_cols)
        
        # One-hot encode categorical variables
        categorical_cols = [c for c in df.columns if c in categorical_params]
        if categorical_cols:
            df = pd.get_dummies(df, columns=categorical_cols, prefix=categorical_cols)
        
        # Store for later use
        self.parameter_matrix = df
        self.feature_names = list(df.columns)
        
        logger.info(f"Created parameter matrix: {df.shape[0]} samples × {df.shape[1]} features")
        logger.info(f"Features: {self.feature_names[:10]}...")  # Show first 10
        
        return df
    
    def _extract_param_value(self, item: Dict, param_name: str) -> Any:
        """Extract parameter value from nested dictionary structure."""
        # Direct lookup
        if param_name in item:
            return item[param_name]
        
        # Check in 'parameters' subdict
        if 'parameters' in item and isinstance(item['parameters'], dict):
            if param_name in item['parameters']:
                param_data = item['parameters'][param_name]
                # Handle ParameterWithEvidence format
                if isinstance(param_data, dict) and 'value' in param_data:
                    return param_data['value']
                return param_data
        
        # Check in nested structures (perturbation, feedback, etc.)
        for nested_key in ['perturbation', 'feedback', 'trials', 'equipment']:
            if nested_key in item and isinstance(item[nested_key], dict):
                if param_name in item[nested_key]:
                    return item[nested_key][param_name]
                # Also check without nested prefix
                param_short = param_name.replace(f'{nested_key}_', '')
                if param_short in item[nested_key]:
                    return item[nested_key][param_short]
        
        return None
    
    def run_pca(self, n_components: int = 3, use_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Perform PCA on parameter matrix.
        
        Args:
            n_components: Number of principal components
            use_matrix: Custom parameter matrix (if None, uses self.parameter_matrix)
            
        Returns:
            Dictionary with PCA results
        """
        if use_matrix is None:
            if self.parameter_matrix is None:
                self.create_parameter_matrix()
            X = self.parameter_matrix.values
        else:
            X = use_matrix.values
        
        # Standardize
        X_scaled = self.scaler.fit_transform(X)
        
        # PCA
        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X_scaled)
        
        results = {
            'components': X_pca,
            'explained_variance': pca.explained_variance_ratio_,
            'cumulative_variance': np.cumsum(pca.explained_variance_ratio_),
            'loadings': pca.components_,
            'feature_names': self.feature_names,
            'n_components': n_components
        }
        
        # Log summary
        total_var = results['cumulative_variance'][-1]
        logger.info(f"PCA: {n_components} components explain {total_var:.1%} of variance")
        for i, var in enumerate(results['explained_variance']):
            logger.info(f"  PC{i+1}: {var:.1%}")
        
        return results
    
    def run_tsne(self, n_components: int = 2, perplexity: int = 30, 
                 use_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Perform t-SNE on parameter matrix.
        
        Args:
            n_components: Number of dimensions (typically 2 or 3)
            perplexity: t-SNE perplexity parameter
            use_matrix: Custom parameter matrix
            
        Returns:
            Dictionary with t-SNE results
        """
        if use_matrix is None:
            if self.parameter_matrix is None:
                self.create_parameter_matrix()
            X = self.parameter_matrix.values
        else:
            X = use_matrix.values
        
        # Standardize
        X_scaled = self.scaler.fit_transform(X)
        
        # t-SNE
        tsne = TSNE(n_components=n_components, perplexity=perplexity, random_state=42)
        X_tsne = tsne.fit_transform(X_scaled)
        
        results = {
            'components': X_tsne,
            'perplexity': perplexity,
            'n_components': n_components
        }
        
        logger.info(f"t-SNE: reduced to {n_components} dimensions (perplexity={perplexity})")
        
        return results
    
    def run_umap(self, n_components: int = 2, n_neighbors: int = 15,
                 use_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Perform UMAP on parameter matrix.
        
        Args:
            n_components: Number of dimensions
            n_neighbors: UMAP n_neighbors parameter
            use_matrix: Custom parameter matrix
            
        Returns:
            Dictionary with UMAP results
        """
        try:
            import umap
        except ImportError:
            raise ImportError("UMAP not installed. Install with: pip install umap-learn")
        
        if use_matrix is None:
            if self.parameter_matrix is None:
                self.create_parameter_matrix()
            X = self.parameter_matrix.values
        else:
            X = use_matrix.values
        
        # Standardize
        X_scaled = self.scaler.fit_transform(X)
        
        # UMAP
        reducer = umap.UMAP(n_components=n_components, n_neighbors=n_neighbors, random_state=42)
        X_umap = reducer.fit_transform(X_scaled)
        
        results = {
            'components': X_umap,
            'n_neighbors': n_neighbors,
            'n_components': n_components
        }
        
        logger.info(f"UMAP: reduced to {n_components} dimensions (n_neighbors={n_neighbors})")
        
        return results
    
    def cluster_hierarchical(self, n_clusters: int = 5, 
                            linkage: str = 'ward',
                            use_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Perform hierarchical clustering.
        
        Args:
            n_clusters: Number of clusters
            linkage: Linkage criterion ('ward', 'complete', 'average')
            use_matrix: Custom parameter matrix
            
        Returns:
            Dictionary with clustering results
        """
        if use_matrix is None:
            if self.parameter_matrix is None:
                self.create_parameter_matrix()
            X = self.parameter_matrix.values
        else:
            X = use_matrix.values
        
        # Standardize
        X_scaled = self.scaler.fit_transform(X)
        
        # Hierarchical clustering
        clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage)
        labels = clustering.fit_predict(X_scaled)
        
        # Calculate silhouette score
        if len(set(labels)) > 1:
            silhouette = silhouette_score(X_scaled, labels)
        else:
            silhouette = 0.0
        
        results = {
            'labels': labels,
            'n_clusters': n_clusters,
            'linkage': linkage,
            'silhouette_score': silhouette
        }
        
        logger.info(f"Hierarchical clustering: {n_clusters} clusters, silhouette={silhouette:.3f}")
        
        return results
    
    def cluster_kmeans(self, n_clusters: int = 5,
                      use_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Perform k-means clustering.
        
        Args:
            n_clusters: Number of clusters
            use_matrix: Custom parameter matrix
            
        Returns:
            Dictionary with clustering results
        """
        if use_matrix is None:
            if self.parameter_matrix is None:
                self.create_parameter_matrix()
            X = self.parameter_matrix.values
        else:
            X = use_matrix.values
        
        # Standardize
        X_scaled = self.scaler.fit_transform(X)
        
        # K-means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        # Calculate silhouette score
        if len(set(labels)) > 1:
            silhouette = silhouette_score(X_scaled, labels)
        else:
            silhouette = 0.0
        
        results = {
            'labels': labels,
            'n_clusters': n_clusters,
            'centroids': kmeans.cluster_centers_,
            'inertia': kmeans.inertia_,
            'silhouette_score': silhouette
        }
        
        logger.info(f"K-means clustering: {n_clusters} clusters, silhouette={silhouette:.3f}, inertia={kmeans.inertia_:.2f}")
        
        return results
    
    def plot_pca_2d(self, pca_results: Dict[str, Any], 
                    color_by: str = None,
                    title: str = "Design Space (PCA)",
                    save_path: str = None):
        """
        Plot 2D PCA visualization.
        
        Args:
            pca_results: Results from run_pca()
            color_by: Parameter name to color points by
            title: Plot title
            save_path: Path to save figure
        """
        components = pca_results['components']
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Get colors
        if color_by:
            color_values = self._get_color_values(color_by)
            scatter = ax.scatter(components[:, 0], components[:, 1],
                               c=color_values, cmap='viridis', s=100, alpha=0.6)
            plt.colorbar(scatter, ax=ax, label=color_by)
        else:
            ax.scatter(components[:, 0], components[:, 1],
                      s=100, alpha=0.6)
        
        # Labels
        var1 = pca_results['explained_variance'][0]
        var2 = pca_results['explained_variance'][1]
        ax.set_xlabel(f'PC1 ({var1:.1%} variance)')
        ax.set_ylabel(f'PC2 ({var2:.1%} variance)')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved PCA plot to {save_path}")
        
        return fig, ax
    
    def plot_pca_3d(self, pca_results: Dict[str, Any],
                    color_by: str = None,
                    title: str = "Design Space (3D PCA)",
                    save_path: str = None):
        """
        Plot 3D PCA visualization.
        
        Args:
            pca_results: Results from run_pca() with n_components>=3
            color_by: Parameter name to color points by
            title: Plot title
            save_path: Path to save figure
        """
        from mpl_toolkits.mplot3d import Axes3D
        
        components = pca_results['components']
        
        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection='3d')
        
        # Get colors
        if color_by:
            color_values = self._get_color_values(color_by)
            scatter = ax.scatter(components[:, 0], components[:, 1], components[:, 2],
                               c=color_values, cmap='viridis', s=100, alpha=0.6)
            fig.colorbar(scatter, ax=ax, label=color_by, pad=0.1)
        else:
            ax.scatter(components[:, 0], components[:, 1], components[:, 2],
                      s=100, alpha=0.6)
        
        # Labels
        var1 = pca_results['explained_variance'][0]
        var2 = pca_results['explained_variance'][1]
        var3 = pca_results['explained_variance'][2]
        ax.set_xlabel(f'PC1 ({var1:.1%})')
        ax.set_ylabel(f'PC2 ({var2:.1%})')
        ax.set_zlabel(f'PC3 ({var3:.1%})')
        ax.set_title(title)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved 3D PCA plot to {save_path}")
        
        return fig, ax
    
    def _get_color_values(self, param_name: str) -> np.ndarray:
        """Extract color values from data source based on parameter name."""
        data_source = self.groups if self.level == 'group' and self.groups else self.experiments
        
        values = []
        for item in data_source:
            value = self._extract_param_value(item, param_name)
            if value is not None:
                values.append(value)
            else:
                values.append(0)  # Default for missing
        
        # Convert to numeric if possible
        try:
            return np.array([float(v) for v in values])
        except (ValueError, TypeError):
            # Categorical - encode as integers
            encoder = LabelEncoder()
            return encoder.fit_transform(values)
    
    def plot_scree(self, pca_results: Dict[str, Any], save_path: str = None):
        """
        Plot scree plot showing variance explained by each component.
        
        Args:
            pca_results: Results from run_pca()
            save_path: Path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        n_components = len(pca_results['explained_variance'])
        x = np.arange(1, n_components + 1)
        
        # Bar plot of variance explained
        ax.bar(x, pca_results['explained_variance'], alpha=0.6, label='Individual')
        ax.plot(x, pca_results['cumulative_variance'], 'ro-', label='Cumulative')
        
        ax.set_xlabel('Principal Component')
        ax.set_ylabel('Variance Explained')
        ax.set_title('Scree Plot')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved scree plot to {save_path}")
        
        return fig, ax
    
    def get_top_features(self, pca_results: Dict[str, Any], 
                        component: int = 0, n_top: int = 10) -> List[Tuple[str, float]]:
        """
        Get top contributing features for a principal component.
        
        Args:
            pca_results: Results from run_pca()
            component: Which component to analyze (0-indexed)
            n_top: Number of top features to return
            
        Returns:
            List of (feature_name, loading) tuples
        """
        loadings = pca_results['loadings'][component]
        feature_names = pca_results['feature_names']
        
        # Get absolute loadings and sort
        abs_loadings = np.abs(loadings)
        top_indices = np.argsort(abs_loadings)[::-1][:n_top]
        
        top_features = [
            (feature_names[i], loadings[i])
            for i in top_indices
        ]
        
        return top_features
