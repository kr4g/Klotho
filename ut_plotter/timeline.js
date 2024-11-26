class TemporalUnitTimeline {
    constructor(container) {
        this.container = d3.select(container);
        this.margin = { top: 40, right: 20, bottom: 20, left: 20 };
        this.width = 800 - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;
        
        // Initialize transform state
        this.currentTransform = d3.zoomIdentity;
        
        // Create base timeline scale (0 to 60 seconds by default)
        this.xScale = d3.scaleLinear()
            .domain([0, 60])
            .range([0, this.width]);
        
        // Setup zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 50])
            .on('zoom', (event) => this.handleZoom(event));
            
        this.setupSVG();
    }

    setupSVG() {
        // Create main SVG
        this.mainSvg = this.container
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .call(this.zoom);  // Add zoom behavior to main SVG

        // Create a group for the visualization
        this.svg = this.mainSvg
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
            
        // Create clip path
        this.mainSvg.append('defs')
            .append('clipPath')
            .attr('id', 'clip')
            .append('rect')
            .attr('width', this.width)
            .attr('height', this.height)
            .attr('x', 0)
            .attr('y', 0);
            
        // Create content group for UTs
        this.contentGroup = this.svg
            .append('g')
            .attr('clip-path', 'url(#clip)');

        // Create axis group (will not be clipped)
        this.axisGroup = this.svg
            .append('g')
            .attr('class', 'x-axis')
            .call(d3.axisTop(this.xScale).tickFormat(d => d.toFixed(1)));
    }

    handleZoom(event) {
        // Update the transform
        this.currentTransform = event.transform;
        
        // Update the axis with the new scale
        const newXScale = event.transform.rescaleX(this.xScale);
        this.axisGroup.call(
            d3.axisTop(newXScale)
                .tickFormat(d => d.toFixed(1))
        );
        
        // Transform the content group
        this.contentGroup.attr('transform', event.transform);
    }

    visualize(uts) {
        if (!uts || uts.length === 0) return;

        // Clear previous content
        this.contentGroup.selectAll('*').remove();

        const barHeight = 30;
        const spacing = 45;

        // Create color scale
        const allRatios = new Set(uts.flatMap(ut => 
            ut.events.map(event => event.metric_ratio)
        ));
        const colorScale = d3.scaleOrdinal()
            .domain([...allRatios])
            .range(d3.schemePastel1);

        // Draw UTs
        uts.forEach((ut, i) => {
            // Draw events
            this.contentGroup.selectAll(`.events-${i}`)
                .data(ut.events)
                .enter()
                .append('rect')
                .attr('x', d => this.xScale(d.start))
                .attr('y', i * spacing)
                .attr('width', d => this.xScale(d.start + d.duration) - this.xScale(d.start))
                .attr('height', barHeight)
                .attr('fill', d => colorScale(d.metric_ratio))
                .attr('stroke', 'white')
                .attr('stroke-width', 0.75);

            // Add labels
            this.contentGroup.selectAll(`.labels-${i}`)
                .data(ut.events)
                .enter()
                .append('text')
                .attr('x', d => this.xScale(d.start + d.duration/2))
                .attr('y', i * spacing + barHeight/2)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .attr('fill', 'black')
                .text(d => d.metric_ratio);
        });
    }
}