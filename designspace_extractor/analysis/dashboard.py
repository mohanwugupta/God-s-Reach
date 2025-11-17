"""
Interactive Design Space Visualization Dashboard

Streamlit app for exploring motor learning design space.

Usage:
    streamlit run analysis/dashboard.py
    
Features:
- Interactive PCA/t-SNE/UMAP plots
- Parameter distribution visualizations
- Clustering analysis
- Group-level comparisons
- Export capabilities
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.design_space import DesignSpaceAnalyzer

st.set_page_config(
    page_title="Motor Learning Design Space Explorer",
    page_icon="🧠",
    layout="wide"
)

# Title
st.title("🧠 Motor Learning Design Space Explorer")
st.markdown("---")

# Sidebar - Data loading
st.sidebar.header("📊 Data Source")

data_source = st.sidebar.radio(
    "Load data from:",
    ["Database", "JSON File"]
)

if data_source == "Database":
    db_path = st.sidebar.text_input(
        "Database path",
        value="out/designspace.db"
    )
    load_button = st.sidebar.button("Load Database")
else:
    json_path = st.sidebar.file_uploader(
        "Upload JSON file",
        type=['json']
    )
    load_button = json_path is not None

# Analysis level
analysis_level = st.sidebar.selectbox(
    "Analysis level",
    ["group", "experiment"]
)

# Initialize analyzer
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None

if load_button:
    with st.spinner("Loading data..."):
        try:
            analyzer = DesignSpaceAnalyzer(level=analysis_level)
            
            if data_source == "Database":
                analyzer.load_from_database(db_path)
            else:
                # Save uploaded file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
                    tmp.write(json_path.read())
                    tmp_path = tmp.name
                analyzer.load_from_json(tmp_path)
            
            # Create parameter matrix
            analyzer.create_parameter_matrix()
            
            st.session_state.analyzer = analyzer
            st.sidebar.success(f"✅ Loaded {len(analyzer.groups if analysis_level == 'group' else analyzer.experiments)} samples")
        
        except Exception as e:
            st.sidebar.error(f"❌ Error loading data: {e}")

# Main content
if st.session_state.analyzer is None:
    st.info("👈 Please load data from the sidebar to begin")
else:
    analyzer = st.session_state.analyzer
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Dimensionality Reduction",
        "🎯 Clustering",
        "📊 Parameter Distributions",
        "🔍 Sample Details"
    ])
    
    # Tab 1: Dimensionality Reduction
    with tab1:
        st.header("Dimensionality Reduction")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Settings")
            
            method = st.selectbox(
                "Method",
                ["PCA", "t-SNE", "UMAP"]
            )
            
            n_components = st.slider(
                "Dimensions",
                min_value=2,
                max_value=3,
                value=2
            )
            
            color_by = st.selectbox(
                "Color by",
                ["None"] + analyzer.feature_names[:20]  # Show first 20 features
            )
            color_param = None if color_by == "None" else color_by
            
            run_button = st.button("Run Analysis", key="dim_red")
        
        with col2:
            if run_button:
                with st.spinner(f"Running {method}..."):
                    if method == "PCA":
                        results = analyzer.run_pca(n_components=max(n_components, 3))
                    elif method == "t-SNE":
                        perplexity = st.sidebar.slider("t-SNE perplexity", 5, 50, 30)
                        results = analyzer.run_tsne(n_components=n_components, perplexity=perplexity)
                    else:  # UMAP
                        n_neighbors = st.sidebar.slider("UMAP n_neighbors", 5, 50, 15)
                        results = analyzer.run_umap(n_components=n_components, n_neighbors=n_neighbors)
                    
                    # Get colors
                    if color_param:
                        colors = analyzer._get_color_values(color_param)
                    else:
                        colors = None
                    
                    # Create plot
                    components = results['components']
                    
                    if n_components == 2:
                        fig = px.scatter(
                            x=components[:, 0],
                            y=components[:, 1],
                            color=colors,
                            labels={'x': f'{method}1', 'y': f'{method}2', 'color': color_param},
                            title=f"Design Space ({method})"
                        )
                    else:  # 3D
                        fig = px.scatter_3d(
                            x=components[:, 0],
                            y=components[:, 1],
                            z=components[:, 2],
                            color=colors,
                            labels={'x': f'{method}1', 'y': f'{method}2', 'z': f'{method}3', 'color': color_param},
                            title=f"Design Space (3D {method})"
                        )
                    
                    fig.update_layout(height=600)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show variance explained (for PCA)
                    if method == "PCA":
                        st.subheader("Variance Explained")
                        var_df = pd.DataFrame({
                            'Component': [f'PC{i+1}' for i in range(len(results['explained_variance']))],
                            'Variance': results['explained_variance'],
                            'Cumulative': results['cumulative_variance']
                        })
                        st.dataframe(var_df, use_container_width=True)
                        
                        # Top contributing features
                        st.subheader("Top Contributing Features (PC1)")
                        top_features = analyzer.get_top_features(results, component=0, n_top=10)
                        features_df = pd.DataFrame(top_features, columns=['Feature', 'Loading'])
                        st.dataframe(features_df, use_container_width=True)
    
    # Tab 2: Clustering
    with tab2:
        st.header("Clustering Analysis")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Settings")
            
            cluster_method = st.selectbox(
                "Method",
                ["K-Means", "Hierarchical"]
            )
            
            n_clusters = st.slider(
                "Number of clusters",
                min_value=2,
                max_value=10,
                value=5
            )
            
            if cluster_method == "Hierarchical":
                linkage = st.selectbox(
                    "Linkage",
                    ["ward", "complete", "average", "single"]
                )
            
            cluster_button = st.button("Run Clustering", key="cluster")
        
        with col2:
            if cluster_button:
                with st.spinner(f"Running {cluster_method} clustering..."):
                    if cluster_method == "K-Means":
                        cluster_results = analyzer.cluster_kmeans(n_clusters=n_clusters)
                    else:
                        cluster_results = analyzer.cluster_hierarchical(
                            n_clusters=n_clusters,
                            linkage=linkage
                        )
                    
                    # Run PCA for visualization
                    pca_results = analyzer.run_pca(n_components=2)
                    
                    # Plot clusters in PCA space
                    fig = px.scatter(
                        x=pca_results['components'][:, 0],
                        y=pca_results['components'][:, 1],
                        color=cluster_results['labels'].astype(str),
                        labels={'x': 'PC1', 'y': 'PC2', 'color': 'Cluster'},
                        title=f"Clusters in PCA Space ({cluster_method})"
                    )
                    fig.update_layout(height=600)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Cluster metrics
                    st.subheader("Clustering Metrics")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Silhouette Score", f"{cluster_results['silhouette_score']:.3f}")
                    with col_b:
                        st.metric("Number of Clusters", n_clusters)
                    
                    # Cluster sizes
                    st.subheader("Cluster Sizes")
                    cluster_counts = pd.Series(cluster_results['labels']).value_counts().sort_index()
                    st.bar_chart(cluster_counts)
    
    # Tab 3: Parameter Distributions
    with tab3:
        st.header("Parameter Distributions")
        
        # Select parameter
        param_name = st.selectbox(
            "Select parameter",
            analyzer.feature_names
        )
        
        if param_name:
            # Get parameter values
            param_values = analyzer.parameter_matrix[param_name].values
            
            # Create histogram
            fig = px.histogram(
                x=param_values,
                nbins=30,
                labels={'x': param_name},
                title=f"Distribution of {param_name}"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistics
            st.subheader("Statistics")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Mean", f"{np.mean(param_values):.2f}")
            with col2:
                st.metric("Std Dev", f"{np.std(param_values):.2f}")
            with col3:
                st.metric("Min", f"{np.min(param_values):.2f}")
            with col4:
                st.metric("Max", f"{np.max(param_values):.2f}")
    
    # Tab 4: Sample Details
    with tab4:
        st.header("Sample Details")
        
        # Show parameter matrix
        st.subheader("Parameter Matrix")
        st.dataframe(analyzer.parameter_matrix, use_container_width=True)
        
        # Download button
        csv = analyzer.parameter_matrix.to_csv()
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="parameter_matrix.csv",
            mime="text/csv"
        )
        
        # Sample counts
        st.subheader("Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Samples", analyzer.parameter_matrix.shape[0])
        with col2:
            st.metric("Total Features", analyzer.parameter_matrix.shape[1])

# Footer
st.markdown("---")
st.markdown(
    """
    **Motor Learning Design Space Explorer** | 
    Built with Streamlit and Plotly | 
    Data from design space parameter extraction
    """
)
